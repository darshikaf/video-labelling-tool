import { useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { Box, CircularProgress } from '@mui/material'
import { RootState } from '@/store/store'
import { getCurrentUser } from '@/store/slices/authSlice'

interface AuthGuardProps {
  children: ReactNode
}

export const AuthGuard = ({ children }: AuthGuardProps) => {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { user, token, loading } = useSelector((state: RootState) => state.auth)

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }

    if (!user && token) {
      dispatch(getCurrentUser())
    }
  }, [token, user, dispatch, navigate])

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="50vh"
      >
        <CircularProgress />
      </Box>
    )
  }

  if (!token || !user) {
    return null
  }

  return <>{children}</>
}