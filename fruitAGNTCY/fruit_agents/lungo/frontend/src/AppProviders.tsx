/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import "@fontsource/inter/400.css"
import "@fontsource/inter/500.css"
import "@fontsource/inter/600.css"
import "@fontsource/inter/700.css"
import "@fontsource/merriweather/400.css"
import "@fontsource/merriweather/700.css"
import "@fontsource/merriweather/900.css"

import React from "react"
import { BrowserRouter } from "react-router-dom"
import { ThemeProvider } from "@/contexts/ThemeContext"
import { MuiThemeBridge } from "@/contexts/MuiThemeBridge"

interface AppProvidersProps {
  children: React.ReactNode
}

const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <MuiThemeBridge>{children}</MuiThemeBridge>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default AppProviders
