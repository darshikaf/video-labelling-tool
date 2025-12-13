import { logout } from '@/store/slices/authSlice'
import { RootState } from '@/store/store'
import { Home, Logout } from '@mui/icons-material'
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Divider,
  Menu,
  MenuItem,
  Toolbar,
  Typography
} from '@mui/material'
import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'

export const Navbar = () => {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { user, token } = useSelector((state: RootState) => state.auth)

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const menuOpen = Boolean(anchorEl)

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleLogout = () => {
    handleMenuClose()
    dispatch(logout())
    navigate('/login')
  }

  const handleGoHome = () => {
    handleMenuClose()
    navigate('/')
  }

  // Get user display name (email or first part of email)
  const displayName = user?.email?.split('@')[0] || 'User'

  return (
    <AppBar position="static">
      <Toolbar>
        {/* App Title - Click to go home */}
        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          Medical Video Annotation Tool
        </Typography>

        {/* User section - only show if logged in */}
        {token && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* User button with dropdown menu */}
            <Button
              color="inherit"
              onClick={handleMenuOpen}
              startIcon={
                <Avatar
                  sx={{ width: 28, height: 28, bgcolor: 'primary.dark' }}
                >
                  {displayName[0].toUpperCase()}
                </Avatar>
              }
              sx={{ textTransform: 'none' }}
            >
              {displayName}
            </Button>

            {/* Dropdown Menu */}
            <Menu
              anchorEl={anchorEl}
              open={menuOpen}
              onClose={handleMenuClose}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
            >
              <MenuItem disabled sx={{ opacity: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Signed in as
                </Typography>
              </MenuItem>
              <MenuItem disabled sx={{ opacity: 1, pt: 0 }}>
                <Typography variant="body2" fontWeight="bold">
                  {user?.email || 'Unknown'}
                </Typography>
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleGoHome}>
                <Home sx={{ mr: 1, fontSize: 20 }} />
                Dashboard
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}>
                <Logout sx={{ mr: 1, fontSize: 20 }} />
                Logout
              </MenuItem>
            </Menu>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  )
}
