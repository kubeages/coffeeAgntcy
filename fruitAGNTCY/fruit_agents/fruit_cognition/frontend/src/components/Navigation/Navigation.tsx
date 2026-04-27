/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Top app bar — MUI AppBar with logo, theme toggle, settings link, and help.
 */

import React, { useState } from "react"
import { Link as RouterLink } from "react-router-dom"
import {
  AppBar,
  Box,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material"
import HelpOutlineIcon from "@mui/icons-material/HelpOutline"
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined"
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined"
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined"
import { Sprout } from "lucide-react"

import { useTheme } from "@/hooks/useTheme"
import InfoModal from "./InfoModal"

const Navigation: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { isLightMode, toggleTheme } = useTheme()

  return (
    <AppBar position="static" sx={{ minHeight: 52 }}>
      <Toolbar variant="dense" sx={{ minHeight: 52, gap: 1 }}>
        <Box
          component={RouterLink}
          to="/"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            flexGrow: 1,
            textDecoration: "none",
            color: "inherit",
          }}
          aria-label="fruitCognition home"
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              bgcolor: "#fcefe1",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#4cbb6c",
            }}
          >
            <Sprout size={20} strokeWidth={2} />
          </Box>
          <Typography
            variant="h6"
            sx={{
              fontFamily: '"Merriweather", "Georgia", serif',
              fontWeight: 700,
              fontSize: "1.05rem",
              letterSpacing: -0.2,
              "& span": { color: "#4cbb6c" },
            }}
          >
            fruit<span>Cognition</span>
          </Typography>
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
