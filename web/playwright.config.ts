import { defineConfig } from "@playwright/test";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3002";
export default defineConfig({
  testDir:"./e2e",fullyParallel:false,workers:1,timeout:90_000,
  reporter:[["list"],["html",{open:"never"}]],
  use:{baseURL,trace:"retain-on-failure"},
  projects:[
    {name:"desktop",use:{viewport:{width:1440,height:900}}},
    {name:"tablet",use:{viewport:{width:768,height:1024},isMobile:true,hasTouch:true}},
    {name:"mobile",use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}},
  ],
  webServer:{command:"node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3002",url:baseURL,reuseExistingServer:process.env.CI !== "true",timeout:120_000},
});
