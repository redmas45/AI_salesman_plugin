const esbuild = require("esbuild");

esbuild
  .build({
    entryPoints: ["src/index.js"],
    bundle: true,
    minify: true,
    outfile: "shopbot.js",
    format: "iife", // immediately-invoked function expression
    target: ["es2020"],
  })
  .then(() => process.stdout.write("Plugin built successfully!\n"))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
