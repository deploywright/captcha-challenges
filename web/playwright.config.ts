import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir:"./e2e",fullyParallel:false,workers:1,timeout:90_000,
  reporter:[["list"],["html",{open:"never"}]],
  use:{baseURL:"http://127.0.0.1:3001",trace:"retain-on-failure"},
  projects:[
    {name:"desktop",use:{viewport:{width:1440,height:900}}},
    {name:"tablet",use:{viewport:{width:768,height:1024},isMobile:true,hasTouch:true}},
    {name:"mobile",use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}},
  ],
  webServer:{command:"npm run dev -- --hostname 127.0.0.1 --port 3001",url:"http://127.0.0.1:3001",reuseExistingServer:!process.env.CI,timeout:120_000},
});
