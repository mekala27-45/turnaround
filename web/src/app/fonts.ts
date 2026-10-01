// The type, self hosted at build time through next/font from the Fontsource packages: Libre Franklin
// for headlines, the interface and chart annotations; Spectral for the long read and the memo;
// Courier Prime for figures in dense tables, hashes, the SQL and code.
import localFont from "next/font/local";

export const franklin = localFont({
  src: [
    { path: "../../node_modules/@fontsource-variable/libre-franklin/files/libre-franklin-latin-wght-normal.woff2", style: "normal" },
    { path: "../../node_modules/@fontsource-variable/libre-franklin/files/libre-franklin-latin-wght-italic.woff2", style: "italic" },
  ],
  weight: "100 900",
  variable: "--font-franklin",
  display: "swap",
});

export const spectral = localFont({
  src: [
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-400-italic.woff2", weight: "400", style: "italic" },
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../node_modules/@fontsource/spectral/files/spectral-latin-600-italic.woff2", weight: "600", style: "italic" },
  ],
  variable: "--font-spectral",
  display: "swap",
});

export const courier = localFont({
  src: [
    { path: "../../node_modules/@fontsource/courier-prime/files/courier-prime-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../node_modules/@fontsource/courier-prime/files/courier-prime-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-courier",
  display: "swap",
});
