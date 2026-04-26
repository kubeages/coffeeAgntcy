/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Top app bar — MUI AppBar with logo, theme toggle, settings link, and help.
 */

import React, { useState } from "react"
import { Link as RouterLink } from "react-router-dom"
import { AppBar, Box, IconButton, Stack, Toolbar, Tooltip } from "@mui/material"
import HelpOutlineIcon from "@mui/icons-material/HelpOutline"
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined"
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined"
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined"

import fruitAgntcyLogo from "@/assets/fruitAGNTCY_logo.svg"
import { useTheme } from "@/hooks/useTheme"
import InfoModal from "./InfoModal"

const Navigation: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { isLightMode, toggleTheme } = useTheme()

  return (
    <AppBar position="static" sx={{ minHeight: 52 }}>
      <Toolbar variant="dense" sx={{ minHeight: 52, gap: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", flexGrow: 1 }}>
          <img
            src={fruitAgntcyLogo}
            alt="Fruit AGNTCY"
            style={{ height: 36, width: "auto" }}
          />
        </Box>

        <Stack direction="row" spacing={0.5}>
          <Tooltip title={`Switch to ${isLightMode ? "dark" : "light"} mode`}>
            <IconButton size="small" onClick={toggleTheme}>
              {isLightMode ? (
                <DarkModeOutlinedIcon fontSize="small" />
              ) : (
                <LightModeOutlinedIcon fontSize="small" />
              )}
            </IconButton>
          </Tooltip>
          <Tooltip title="Settings">
            <IconButton
              size="small"
              component={RouterLink}
              to="/admin"
              aria-label="Settings"
            >
              <SettingsOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Help">
            <IconButton
              size="small"
              onClick={() => setIsModalOpen(true)}
              aria-label="Help"
            >
              <HelpOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Toolbar>

      <InfoModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </AppBar>
  )
}

export default Navigation
