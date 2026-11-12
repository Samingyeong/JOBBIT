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
  // React 규칙: 아직 React 코드는 없음. .jsx가 생기면 자동 적용.
  // .tsx는 TypeScript 파서(typescript-eslint)가 필요하므로 TS 도입 단계에서 추가.
  {
    files: ['**/*.jsx'],
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
