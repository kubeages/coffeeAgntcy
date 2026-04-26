/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Bridges Lungo's ThemeContext (light/dark/system) into MUI's ThemeProvider
 * so MUI components react to the in-app toggle. Replaces the previous
 * @open-ui-kit/core wrapper.
 */

import type { ReactNode } from "react"
import { ThemeProvider, CssBaseline } from "@mui/material"
import { useTheme } from "@/hooks/useTheme"
import { lightTheme, darkTheme } from "@/contexts/muiTheme"

export function MuiThemeBridge({ children }: { children: ReactNode }) {
  const { isLightMode } = useTheme()
  return (
    <ThemeProvider theme={isLightMode ? lightTheme : darkTheme}>
      <CssBaseline enableColorScheme />
      {children}
    </ThemeProvider>
  )
}
