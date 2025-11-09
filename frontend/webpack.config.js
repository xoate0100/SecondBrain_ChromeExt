const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = (env, argv) => {
  const isProduction = argv.mode === "production";

  return {
    entry: {
      "background/service-worker": "./src/background/service-worker.ts",
      "content/content-script": "./src/content/content-script.ts",
      "popup/popup": "./src/popup/popup.ts",
    },
    output: {
      path: path.resolve(__dirname, "dist"),
      filename: "[name].js",
      clean: true,
    },
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: "ts-loader",
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: ["style-loader", "css-loader"],
          exclude: /node_modules/,
        },
      ],
    },
    resolve: {
      extensions: [".ts", ".js"],
      alias: {
        "@shared": path.resolve(__dirname, "../shared"),
        "@": path.resolve(__dirname, "src"),
      },
    },
    plugins: [
      new CopyWebpackPlugin({
        patterns: [
          { from: "src/popup/popup.html", to: "popup/popup.html" },
          { from: "src/styles/popup.css", to: "styles/popup.css" },
          { from: "src/styles/content.css", to: "styles/content.css" },
          { from: "manifest.json", to: "manifest.json" },
          { from: "icons", to: "icons", noErrorOnMissing: true },
        ],
      }),
    ],
    devtool: isProduction ? false : "source-map",
    optimization: {
      minimize: isProduction,
    },
    stats: {
      errorDetails: true,
    },
  };
};
