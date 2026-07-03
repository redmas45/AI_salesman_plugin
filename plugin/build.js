const esbuild = require("esbuild");

const BROWSER_BUNDLE_TARGET = ["es2020"];
const IIFE_FORMAT = "iife";

const bundles = [
  {
    entryPoints: ["src/index.js"],
    outfile: "mayabot.js",
  },
  {
    entryPoints: ["src/adapter/index.js"],
    outfile: "mayabot-adapter.js",
  },
];

async function buildBundle(bundle) {
  await esbuild.build({
    ...bundle,
    bundle: true,
    minify: true,
    format: IIFE_FORMAT,
    target: BROWSER_BUNDLE_TARGET,
  });
}

Promise.all(bundles.map(buildBundle))
  .then(() => process.stdout.write("Plugin bundles built successfully!\n"))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
