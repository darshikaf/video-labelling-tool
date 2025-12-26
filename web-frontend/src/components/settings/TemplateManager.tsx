import { CategoryTemplate, templateAPI } from '@/utils/api'
import {
  Add,
  CheckCircle,
  Delete,
  ExpandMore,
  LocalOffer,
} from '@mui/icons-material'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Grid,
  Typography,
} from '@mui/material'
import React, { useEffect, useState } from 'react'

interface TemplateManagerProps {
  projectId: number
  onTemplateApplied?: () => void
}

export const TemplateManager: React.FC<TemplateManagerProps> = ({
  projectId,
  onTemplateApplied,
}) => {
  const [templates, setTemplates] = useState<CategoryTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Apply dialog state
  const [applyDialog, setApplyDialog] = useState<{
    open: boolean
    template: CategoryTemplate | null
  }>({ open: false, template: null })
  const [applying, setApplying] = useState(false)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await templateAPI.getTemplates()
      setTemplates(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load templates')
    } finally {
      setLoading(false)
    }
  }

  const handleApplyClick = (template: CategoryTemplate) => {
    setApplyDialog({ open: true, template })
  }

  const handleApplyConfirm = async (merge: boolean) => {
    if (!applyDialog.template) return

    setApplying(true)
    setError(null)
    try {
      const result = await templateAPI.applyTemplate(
        applyDialog.template.id,
        projectId,
        merge
      )
      setSuccess(
        `Applied "${applyDialog.template.name}": ${result.categories_added} added, ${result.categories_skipped} skipped`
      )
      setApplyDialog({ open: false, template: null })
      onTemplateApplied?.()

      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(null), 5000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to apply template')
    } finally {
      setApplying(false)
    }
  }

  const handleDeleteTemplate = async (template: CategoryTemplate) => {
    if (!confirm(`Delete template "${template.name}"?`)) return

    try {
      await templateAPI.deleteTemplate(template.id)
      await loadTemplates()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete template')
    }
  }

  return (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Box display="flex" alignItems="center" gap={1}>
          <LocalOffer />
          <Typography variant="h6">Category Templates</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Apply a template to quickly add predefined categories to your project.
        </Typography>

        {loading ? (
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress size={24} />
          </Box>
        ) : templates.length === 0 ? (
          <Typography color="text.secondary" textAlign="center" py={2}>
            No templates available. System templates will appear after initial setup.
          </Typography>
        ) : (
          <Grid container spacing={2}>
            {templates.map((template) => (
              <Grid item xs={12} sm={6} key={template.id}>
                <Card variant="outlined">
                  <CardContent sx={{ pb: 1 }}>
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {template.name}
                      </Typography>
                      {template.is_system && (
                        <Chip label="System" size="small" color="primary" variant="outlined" />
                      )}
                    </Box>

                    {template.description && (
                      <Typography variant="body2" color="text.secondary" mb={1}>
                        {template.description}
                      </Typography>
                    )}

                    <Box display="flex" flexWrap="wrap" gap={0.5}>
                      {template.items.slice(0, 6).map((item, idx) => (
                        <Chip
                          key={idx}
                          label={item.name}
                          size="small"
                          sx={{
                            backgroundColor: item.color,
                            color: '#fff',
                            fontSize: '0.7rem',
                          }}
                        />
                      ))}
                      {template.items.length > 6 && (
                        <Chip
                          label={`+${template.items.length - 6} more`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Box>
                  </CardContent>
                  <CardActions sx={{ justifyContent: 'space-between' }}>
                    <Button
                      size="small"
                      startIcon={<Add />}
                      onClick={() => handleApplyClick(template)}
                    >
                      Apply
                    </Button>
                    {!template.is_system && (
                      <Button
                        size="small"
                        color="error"
                        startIcon={<Delete />}
                        onClick={() => handleDeleteTemplate(template)}
                      >
                        Delete
                      </Button>
                    )}
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {/* Apply Template Dialog */}
        <Dialog
          open={applyDialog.open}
          onClose={() => setApplyDialog({ open: false, template: null })}
        >
          <DialogTitle>Apply Template</DialogTitle>
          <DialogContent>
            <DialogContentText>
              How would you like to apply "{applyDialog.template?.name}" to this project?
            </DialogContentText>
            <Box mt={2}>
              <Typography variant="body2" color="text.secondary">
                <strong>Categories to add:</strong>
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={0.5} mt={1}>
                {applyDialog.template?.items.map((item, idx) => (
                  <Chip
                    key={idx}
                    label={item.name}
                    size="small"
                    sx={{ backgroundColor: item.color, color: '#fff' }}
                  />
                ))}
              </Box>
            </Box>
          </DialogContent>
          <DialogActions sx={{ flexDirection: 'column', gap: 1, p: 2 }}>
            <Button
              fullWidth
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleApplyConfirm(true)}
              disabled={applying}
            >
              {applying ? 'Applying...' : 'Merge with Existing Categories'}
            </Button>
            <Button
              fullWidth
              variant="outlined"
              color="warning"
              startIcon={<CheckCircle />}
              onClick={() => handleApplyConfirm(false)}
              disabled={applying}
            >
              Replace (Keep Categories with Annotations)
            </Button>
            <Button
              fullWidth
              onClick={() => setApplyDialog({ open: false, template: null })}
              disabled={applying}
            >
              Cancel
            </Button>
          </DialogActions>
        </Dialog>
      </AccordionDetails>
    </Accordion>
  )
}

export default TemplateManager
