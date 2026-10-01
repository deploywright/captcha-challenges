"""Regression gates for the non-routing visual overhaul and private metadata."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
import pytest
from pydantic import ValidationError

from challenge_engine.core.schemas import Level1Config, Level2AConfig, Level2BConfig, Level3BConfig, TilePrivateMetadata
from challenge_engine.core.exporter import export_challenge_bundle
from challenge_engine.core.validation import validate_single_challenge_dir
from challenge_engine.core.image_prep import prepare_context_crop, compute_rendered_metrics
from challenge_engine.levels.level_1.generator import Level1StreetGridGenerator
from challenge_engine.levels.level_2a.generator import Level2AHardStreetGridGenerator
from challenge_engine.levels.level_2b.generator import Level2BCheckerShadowGenerator
from challenge_engine.levels.level_3b.generator import Level3BDegradedVisionGenerator


def test_context_crop_keeps_circle_round_and_reports_pixels():
    image=Image.new('RGB',(1280,720),'white')
    ImageDraw.Draw(image).ellipse((550,270,650,370),fill='black')
    result=prepare_context_crop(image,(550,270,650,370))
    dark=np.asarray(result.image)[:,:,0]<100
    yy,xx=np.where(dark)
    assert abs((xx.max()-xx.min())-(yy.max()-yy.min())) <= 1
    metrics=compute_rendered_metrics((100,100,200,200),(50,50,250,250))
    assert metrics.rendered_width == metrics.rendered_height == 128


@pytest.mark.parametrize('level',[1,2,3])
def test_actual_street_generators_never_resize_rectangular_frames(sample_bdd100k_root: Path, monkeypatch, level):
    calls=[]; resize=Image.Image.resize
    def checked(image,size,*args,**kwargs):
        calls.append((image.size,size))
        assert image.width == image.height, 'Rectangular full-frame warping'
        return resize(image,size,*args,**kwargs)
    monkeypatch.setattr(Image.Image,'resize',checked)
    classes={1:(Level1Config,Level1StreetGridGenerator),2:(Level2AConfig,Level2AHardStreetGridGenerator),3:(Level3BConfig,Level3BDegradedVisionGenerator)}
    config,generator=classes[level]
    bundle=generator(config(bdd100kRoot=str(sample_bdd100k_root),positiveCount=3)).generate_one(201)
    assert len(bundle.assets)==9 and calls
    for tile in bundle.private_answer.tiles:
        x1,y1,x2,y2=tile.crop_box
        assert x2-x1==y2-y1 and 0<=x1<x2<=1280 and 0<=y1<y2<=720
        if tile.isPositive:
            assert tile.rendered_object_size > 30
        if level==2:
            assert len(tile.difficulty_budget_factors)<=2
            if tile.isPositive: assert tile.difficulty_budget_factors
    TilePrivateMetadata.model_validate(bundle.private_answer.tiles[0].model_dump())
    with pytest.raises(ValidationError):
        TilePrivateMetadata.model_validate({**bundle.private_answer.tiles[0].model_dump(),'unexpected':True})


def test_level_2a_defaults_and_budget_cannot_silently_fall_back(sample_bdd100k_root: Path):
    config=Level2AConfig(bdd100kRoot=str(sample_bdd100k_root))
    assert (config.resolved_rows,config.resolved_columns,config.positiveCount,config.maxDifficultyFactors)==(3,3,3,2)
    generator=Level2AHardStreetGridGenerator(config)
    for seed in (101,202,303):
        assert all(len(t.difficulty_budget_factors)<=2 for t in generator.generate_one(seed).private_answer.tiles)
    config.maxDifficultyFactors=1
    with pytest.raises((ValueError,FileNotFoundError),match='Insufficient|No matching'):
        generator.generate_one(101)


def test_configured_target_and_optional_targets_are_honored(sample_bdd100k_root: Path):
    generator=Level1StreetGridGenerator(Level1Config(bdd100kRoot=str(sample_bdd100k_root),target='bus',positiveCount=3))
    assert generator.generate_one(101).private_answer.targetClass=='bus'
    generator.config.targets=['truck']
    assert generator.generate_one(101).private_answer.targetClass=='truck'


def test_six_illusion_schemas_assets_and_independent_validation(tmp_path: Path):
    generator=Level2BCheckerShadowGenerator(Level2BConfig())
    bundles=generator.generate_batch(6,100)
    assert {b.private_answer.illusion.illusionType for b in bundles}=={'checker-shadow','muller-lyer','ebbinghaus','ponzo','simultaneous-contrast','cafe-wall'}
    for bundle in bundles:
        directory=export_challenge_bundle(bundle,tmp_path,update_manifest=False)
        result=validate_single_challenge_dir(directory)
        assert result.passed,result.errors
        # A changed documented measurement must fail independently of regeneration.
        private=directory/'answer.json'; data=json.loads(private.read_text())
        if data['illusion']['illusionType']!='checker-shadow':
            data['illusion']['measuredValues']['difference']=99
            private.write_text(json.dumps(data))
            assert not validate_single_challenge_dir(directory,check_determinism=False).passed
    assert Level2BConfig(options=['Equal','Different']).options==['Equal','Different']
    with pytest.raises(ValueError,match='Unknown illusion'):
        generator.generate_one(1,'unknown')


def test_all_seven_resolutions_freeze_source_crop_and_order(sample_bdd100k_root: Path):
    generator=Level3BDegradedVisionGenerator(Level3BConfig(bdd100kRoot=str(sample_bdd100k_root)))
    bundles=[generator.generate_one(555,resolution=r) for r in [64,48,32,24,16,12,8]]
    first=bundles[0].private_answer
    for bundle in bundles:
        assert bundle.private_answer.correctSelection==first.correctSelection
        assert [(t.sourceId,t.crop_box,t.isPositive) for t in bundle.private_answer.tiles]==[(t.sourceId,t.crop_box,t.isPositive) for t in first.tiles]
    assert any(not np.array_equal(np.asarray(bundles[0].assets[a]),np.asarray(bundles[-1].assets[a])) for a in bundles[0].assets)


def test_crop_metadata_cannot_leak_into_public_output(tmp_path: Path):
    bundle=Level2BCheckerShadowGenerator(Level2BConfig()).generate_one(100)
    directory=export_challenge_bundle(bundle,tmp_path,update_manifest=False)
    public=directory/'challenge.json'; data=json.loads(public.read_text()); data['crop_box']=[0,0,20,20]
    public.write_text(json.dumps(data))
    result=validate_single_challenge_dir(directory)
    assert not result.passed and any('crop_box' in err for err in result.errors)
