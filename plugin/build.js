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
  .then(() => console.log("Plugin built successfully!"))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
