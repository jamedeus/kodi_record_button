import globals from "globals";
import pluginJs from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname
});

/** @type {import('eslint').Linter.Config[]} */
export default [
  {files: ["**/*.js"], languageOptions: {sourceType: "script"}},
  {languageOptions: { globals: globals.browser }},
  ...compat.extends('eslint-config-airbnb-base'),
  pluginJs.configs.recommended,
  {rules: {
    "indent": ["error", 4],
    "no-multiple-empty-lines": ["error", { "max": 2, "maxEOF": 0 }],
    "camelcase": "off",
    "no-console": "off",
    "import/extensions": "off",
  }}
];
