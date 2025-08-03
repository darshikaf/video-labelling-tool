import { AppBar, Toolbar, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'

export const Navbar = () => {
  const navigate = useNavigate()

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography 
          variant="h6" 
          component="div" 
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          Medical Video Annotation Tool - Prototype
        </Typography>
      </Toolbar>
    </AppBar>
  )
}