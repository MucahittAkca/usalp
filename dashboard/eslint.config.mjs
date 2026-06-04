import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  {
    ignores: [".next/**", "next-env.d.ts", "tsconfig.tsbuildinfo"],
  },
  ...nextVitals,
  {
    rules: {
      "react-hooks/incompatible-library": "off",
    },
  },
];

export default config;
