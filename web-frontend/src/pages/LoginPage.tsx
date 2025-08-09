import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Tabs,
  Tab,
} from '@mui/material'
import { RootState } from '@/store/store'
import { login, register, clearError } from '@/store/slices/authSlice'

export const LoginPage = () => {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { token, loading, error } = useSelector((state: RootState) => state.auth)
  
  const [tabValue, setTabValue] = useState(0)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  useEffect(() => {
    if (token) {
      navigate('/')
    }
  }, [token, navigate])

  useEffect(() => {
    dispatch(clearError())
  }, [tabValue, dispatch])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (tabValue === 1 && password !== confirmPassword) {
      return
    }

    if (tabValue === 0) {
      dispatch(login({ email, password }))
    } else {
      dispatch(register({ email, password }))
    }
  }

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            Medical Video Annotation
          </Typography>
          
          <Tabs
            value={tabValue}
            onChange={(_, newValue) => setTabValue(newValue)}
            variant="fullWidth"
            sx={{ mb: 3 }}
          >
            <Tab label="Login" />
            <Tab label="Register" />
          </Tabs>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {tabValue === 1 && (
              <TextField
                margin="normal"
                required
                fullWidth
                name="confirmPassword"
                label="Confirm Password"
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={password !== confirmPassword && confirmPassword !== ''}
                helperText={
                  password !== confirmPassword && confirmPassword !== ''
                    ? 'Passwords do not match'
                    : ''
                }
              />
            )}
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={
                loading ||
                !email ||
                !password ||
                (tabValue === 1 && password !== confirmPassword)
              }
            >
              {loading ? 'Processing...' : tabValue === 0 ? 'Login' : 'Register'}
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  )
}