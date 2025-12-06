import { Component, ErrorInfo, ReactNode } from 'react'
import { Box, Typography, Button, Card, CardContent } from '@mui/material'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="100vh"
          p={3}
        >
          <Card sx={{ maxWidth: 600 }}>
            <CardContent>
              <Typography variant="h5" gutterBottom color="error">
                Something went wrong
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                {this.state.error?.message || 'An unexpected error occurred'}
              </Typography>
              <Button
                variant="contained"
                onClick={() => {
                  this.setState({ hasError: false, error: null })
                  window.location.reload()
                }}
              >
                Reload Page
              </Button>
            </CardContent>
          </Card>
        </Box>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary

