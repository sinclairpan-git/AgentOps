import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..", "..");

const readText = (path) => readFileSync(resolve(root, path), "utf8");
const readRepoText = (path) => readFileSync(resolve(repoRoot, path), "utf8");

const packageJson = JSON.parse(readText("package.json"));
const packageLock = readText("package-lock.json");
const providerSource = readText("src/provider/enterpriseVue2Provider.js");
const mainSource = readText("src/main.js");
const techStack = readRepoText(".ai-sdlc/profiles/tech-stack.yml");

const vendoredDependencies = {
  "@sxf/er-components": "sxf-er-components-1.27.5.tgz",
  "@sxf/er-config": "sxf-er-config-1.4.0.tgz",
  "@sxf/er-feature": "sxf-er-feature-0.1.0.tgz",
  "@sxf/er-lib": "sxf-er-lib-1.0.0.tgz",
  "@sxf/er-style": "sxf-er-style-1.2.1.tgz",
  "@sxf/er-utils": "sxf-er-utils-1.4.0.tgz",
  "@sxf/er-validator": "sxf-er-validator-1.2.0.tgz",
  "@sxf/er-widget": "sxf-er-widget-1.15.2.tgz",
  "@sxf/intl": "sxf-intl-2.5.3.tgz",
  "@sxf/jquery": "sxf-jquery-1.0.6.tgz",
  "@sxf/sf-theme": "sxf-sf-theme-0.2.5.tgz",
  "@sxf/vtv-icon": "sxf-vtv-icon-1.0.272.tgz",
  "@sxf/vue-intl": "sxf-vue-intl-1.11.4.tgz",
  "@uedc/sf-layout": "uedc-sf-layout-1.15.0.tgz",
  jquery: "sxf-jquery-1.0.6.tgz"
};

for (const [dependencyName, tarballName] of Object.entries(vendoredDependencies)) {
  const expectedSpec = `file:../../vendor/enterprise-vue2/${tarballName}`;
  assert.equal(packageJson.dependencies[dependencyName], expectedSpec, `${dependencyName} must use project-vendor tarball`);
  assert.ok(existsSync(resolve(repoRoot, "vendor/enterprise-vue2", tarballName)), `${tarballName} must exist`);
}

assert.match(providerSource, /allowFullVueUse:\s*false/);
assert.match(providerSource, /installedVersion:\s*"1\.27\.5"/);
assert.doesNotMatch(providerSource, /Vue\.use\(\s*ErComponents\s*\)/);
assert.doesNotMatch(mainSource, /Vue\.use\(\s*ErComponents\s*\)/);
assert.doesNotMatch(packageLock, /registry\.npmjs\.org\/@sxf|registry\.npmjs\.org\/@uedc|@sxf%2f|@uedc%2f|code\.sangfor|mq\.code\.sangfor/);

assert.match(techStack, /source:\s*project-vendor/);
assert.match(techStack, /path:\s*vendor\/enterprise-vue2\/sxf-er-components-1\.27\.5\.tgz/);

assert.ok(existsSync(resolve(root, "src/styles.css")), "src/styles.css must exist because src/main.js imports it");
