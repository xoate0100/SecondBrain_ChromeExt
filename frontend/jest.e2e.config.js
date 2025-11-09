module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/tests/e2e"],
  testMatch: ["**/*.e2e.spec.ts", "**/*.e2e.test.ts"],
  moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json"],
  transform: {
    "^.+\\.ts$": "ts-jest",
  },
  testTimeout: 30000,
  setupFilesAfterEnv: ["<rootDir>/jest.e2e.setup.js"],
};
