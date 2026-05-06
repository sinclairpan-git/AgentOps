import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..", "..");

const readText = (path) => readFileSync(resolve(root, path), "utf8");
const readRepoText = (path) => readFileSync(resolve(repoRoot, path), "utf8");

const packageJson = JSON.parse(readText("package.json"));
const providerSource = readText("src/provider/enterpriseVue2Provider.js");
const mainSource = readText("src/main.js");
const techStack = readRepoText(".ai-sdlc/profiles/tech-stack.yml");

assert.equal(packageJson.dependencies["@sxf/er-components"], "file:../../vendor/enterprise-vue2/sxf-er-components-1.27.5.tgz");
assert.equal(packageJson.dependencies["@sxf/sf-theme"], "file:../../vendor/enterprise-vue2/sxf-sf-theme-0.2.5.tgz");

assert.ok(existsSync(resolve(repoRoot, "vendor/enterprise-vue2/sxf-er-components-1.27.5.tgz")));
assert.ok(existsSync(resolve(repoRoot, "vendor/enterprise-vue2/sxf-sf-theme-0.2.5.tgz")));

assert.match(providerSource, /allowFullVueUse:\s*false/);
assert.match(providerSource, /installedVersion:\s*"1\.27\.5"/);
assert.doesNotMatch(providerSource, /Vue\.use\(\s*ErComponents\s*\)/);
assert.doesNotMatch(mainSource, /Vue\.use\(\s*ErComponents\s*\)/);

assert.match(techStack, /source:\s*project-vendor/);
assert.match(techStack, /path:\s*vendor\/enterprise-vue2\/sxf-er-components-1\.27\.5\.tgz/);

assert.ok(existsSync(resolve(root, "src/styles.css")), "src/styles.css must exist because src/main.js imports it");
