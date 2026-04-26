/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Fruit AGNTCY theme — palette + type cloned from frutascharito.es
 * (Spanish fresh-produce shop). Goal: feel like a clean grocer's site
 * — fresh green primary, warm orange accent, white background, dark
 * gray text, Merriweather serif for headings, sans for body. Avoid the
 * loud gradients / heavy rounding of the previous mango build.
 */

import { createTheme, alpha, type Theme } from "@mui/material/styles"

// Frutas Charito reference palette
const radius = 6 // subtle rounding only

const palette = {
  light: {
    primary: "#4cbb6c", // fresh green
    primaryDark: "#13693c", // hover / pressed
    secondary: "#ff9a52", // warm orange
    info: "#2fb5d2", // soft teal
    warning: "#e8b400",
    error: "#ff4c4c", // red (also used for sale tags on the reference)
    bgDefault: "#ffffff",
    bgPaper: "#ffffff",
    bgSubtle: "#f6f6f6", // section dividers
    divider: "#e6e6e6",
    textPrimary: "#232323",
    textSecondary: "#7a7a7a",
  },
  dark: {
    primary: "#5BC57A",
    primaryDark: "#1F8A4D",
    secondary: "#FFB477",
    info: "#5BC0DE",
    warning: "#F4D35E",
    error: "#FF6E6E",
    bgDefault: "#15171A",
    bgPaper: "#1B1E22",
    bgSubtle: "#22262A",
    divider: "rgba(255,255,255,0.10)",
    textPrimary: "#F2F3F4",
    textSecondary: "#A6ABB2",
  },
} as const

const buildTheme = (mode: "light" | "dark"): Theme => {
  const p = palette[mode]
  return createTheme({
    palette: {
      mode,
      primary: { main: p.primary, dark: p.primaryDark },
      secondary: { main: p.secondary },
      info: { main: p.info },
      warning: { main: p.warning },
      error: { main: p.error },
      background: { default: p.bgDefault, paper: p.bgPaper },
      divider: p.divider,
      text: { primary: p.textPrimary, secondary: p.textSecondary },
    },
    shape: { borderRadius: radius },
    typography: {
      fontFamily:
        '"Inter", "Helvetica Neue", Helvetica, Arial, system-ui, sans-serif',
      h1: {
        fontFamily: '"Merriweather", "Georgia", serif',
        fontWeight: 700,
        letterSpacing: -0.4,
      },
      h2: {
        fontFamily: '"Merriweather", "Georgia", serif',
        fontWeight: 700,
        letterSpacing: -0.3,
      },
      h3: { fontFamily: '"Merriweather", "Georgia", serif', fontWeight: 700 },
      h4: { fontFamily: '"Merriweather", "Georgia", serif', fontWeight: 700 },
      h5: { fontFamily: '"Merriweather", "Georgia", serif', fontWeight: 700 },
      h6: { fontFamily: '"Merriweather", "Georgia", serif', fontWeight: 700 },
      subtitle1: { fontWeight: 600 },
      button: { textTransform: "uppercase", fontWeight: 700, letterSpacing: 0.5 },
    },
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: radius, paddingInline: 16, paddingBlock: 8 },
          contained: {
            boxShadow: "none",
            "&:hover": { boxShadow: "none" },
          },
          containedPrimary: ({ theme }) => ({
            backgroundColor: theme.palette.primary.main,
            color: "#ffffff",
            "&:hover": { backgroundColor: theme.palette.primary.dark },
          }),
          containedSecondary: ({ theme }) => ({
            backgroundColor: theme.palette.secondary.main,
            color: "#ffffff",
            "&:hover": {
              backgroundColor: alpha(theme.palette.secondary.main, 0.85),
            },
          }),
        },
      },
      MuiCard: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: radius,
            backgroundImage: "none",
            border: `1px solid ${theme.palette.divider}`,
            boxShadow:
              theme.palette.mode === "light"
                ? "0 1px 2px rgba(35,35,35,0.04), 0 1px 8px rgba(35,35,35,0.04)"
                : "0 1px 2px rgba(0,0,0,0.5), 0 4px 12px rgba(0,0,0,0.35)",
          }),
        },
      },
      MuiCardHeader: {
        styleOverrides: {
          title: {
            fontFamily: '"Merriweather", "Georgia", serif',
            fontWeight: 700,
            fontSize: "1.15rem",
            letterSpacing: -0.2,
          },
        },
      },
      MuiTextField: {
        defaultProps: { size: "small", variant: "outlined" },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: { borderRadius: radius },
        },
      },
      MuiAppBar: {
        defaultProps: { color: "default", elevation: 0 },
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: theme.palette.background.paper,
            borderBottom: `1px solid ${theme.palette.divider}`,
            color: theme.palette.text.primary,
          }),
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 500, borderRadius: 4 },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: { borderRadius: radius },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: ({ theme }) => ({
            backgroundColor: alpha(theme.palette.text.primary, 0.92),
            color: theme.palette.background.paper,
            fontWeight: 500,
          }),
        },
      },
    },
  })
}

export const lightTheme = buildTheme("light")
export const darkTheme = buildTheme("dark")
