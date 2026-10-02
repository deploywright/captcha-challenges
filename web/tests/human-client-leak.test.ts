import { describe, expect, it } from "vitest";
import ts from "typescript";
import fs from "node:fs";
import path from "node:path";

describe("Human Benchmark browser isolation", () => {
  it("has no transitive runtime import of grading, private registries, or administrative secrets", () => {
    const root = path.resolve("."); const visited = new Set<string>();
    function visit(file: string) {
      if (visited.has(file)) return; visited.add(file);
      expect(file).not.toMatch(/generated-private|validation\.server|\.server\.[tj]sx?$/);
      const text = fs.readFileSync(file,"utf8");
      expect(text).not.toMatch(/getPrivateAnswer|ANSWERS_REGISTRY|HUMAN_BENCHMARK_ADMIN_KEY/);
      const source = ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true);
      for(const statement of source.statements) {
        if (!ts.isImportDeclaration(statement) || !ts.isStringLiteral(statement.moduleSpecifier) || statement.importClause?.isTypeOnly) continue;
        const specifier = statement.moduleSpecifier.text;
        if (!specifier.startsWith(".") && !specifier.startsWith("@/")) continue;
        const base = specifier.startsWith("@/") ? path.join(root,specifier.slice(2)) : path.resolve(path.dirname(file),specifier);
        const imported = [base,`${base}.ts`,`${base}.tsx`,path.join(base,"index.ts")].find(p => fs.existsSync(p) && fs.statSync(p).isFile());
        if (imported) visit(imported);
      }
    }
    for(const file of ["HumanBenchmarkLanding.tsx","HumanBenchmarkPlayer.tsx"]) visit(path.join(root,"components/human-benchmark",file));
    expect(visited.size).toBeGreaterThan(5);
  });
  it("has no private answer identifiers in built browser JavaScript when a build is present", () => {
    const root = path.resolve(".next/static");
    if (!fs.existsSync(root)) return;
    function scan(folder: string) {
      for(const file of fs.readdirSync(folder,{withFileTypes:true})) {
        const full = path.join(folder,file.name);
        if (file.isDirectory()) scan(full);
        else if (file.name.endsWith(".js")) expect(/getPrivateAnswer|ANSWERS_REGISTRY|correctSelection|generated-private/.test(fs.readFileSync(full,"utf8")),full).toBe(false);
      }
    }
    scan(root);
  });
});
