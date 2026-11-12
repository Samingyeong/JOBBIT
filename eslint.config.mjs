import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    ignores: ['node_modules/**', 'src-tauri/target/**', 'src-tauri/gen/**', 'web/data/**', '.review/**'],
  },
  js.configs.recommended,
  {
    files: ['web/**/*.js'],
    languageOptions: { sourceType: 'module', globals: globals.browser },
  },
  {
    files: ['scripts/**/*.mjs', '*.mjs'],
    languageOptions: { globals: globals.node },
  },
  // React 규칙: 아직 React 코드는 없음. jsx/tsx가 생기면 자동 적용.
  {
    files: ['**/*.{jsx,tsx}'],
    plugins: { react, 'react-hooks': reactHooks },
    languageOptions: {
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...react.configs.recommended.rules,
      ...react.configs['jsx-runtime'].rules,
      ...reactHooks.configs.recommended.rules,
    },
  },
];
