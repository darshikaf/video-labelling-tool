import { projectAPI } from '@/utils/api'
import {
  Add,
  Delete,
  Edit,
  Save,
  Cancel,
  ExpandMore,
} from '@mui/icons-material'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  ListItemText,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material'
import React, { useEffect, useState } from 'react'

interface Category {
  id: number
  name: string
  color: string
}

interface CategoryManagerProps {
  projectId: number
  onCategoriesChange?: (categories: Category[]) => void
}

// Predefined colors for easy selection
const PRESET_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
  '#DDA0DD', '#98D8C8', '#F7DC6F', '#FF8C42', '#6C5CE7',
  '#A8E6CF', '#FFD93D', '#FF6B6B', '#C44569', '#546DE5',
]

export const CategoryManager: React.FC<CategoryManagerProps> = ({
  projectId,
  onCategoriesChange,
}) => {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Add/Edit state
  const [isAdding, setIsAdding] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formName, setFormName] = useState('')
  const [formColor, setFormColor] = useState('#4ECDC4')

  // Delete dialog state
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; category: Category | null }>({
    open: false,
    category: null,
  })
  const [forceDelete, setForceDelete] = useState(false)

  // Load categories
  useEffect(() => {
    loadCategories()
  }, [projectId])

  const loadCategories = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await projectAPI.getProjectCategories(projectId)
      setCategories(data)
      onCategoriesChange?.(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load categories')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setIsAdding(true)
    setFormName('')
    setFormColor(PRESET_COLORS[categories.length % PRESET_COLORS.length])
  }

  const handleEdit = (category: Category) => {
    setEditingId(category.id)
    setFormName(category.name)
    setFormColor(category.color)
  }

  const handleCancel = () => {
    setIsAdding(false)
    setEditingId(null)
    setFormName('')
    setFormColor('#4ECDC4')
  }

  const handleSave = async () => {
    if (!formName.trim()) {
      setError('Category name is required')
      return
    }

    setLoading(true)
    setError(null)
    try {
      if (isAdding) {
        await projectAPI.createCategory(projectId, formName.trim(), formColor)
      } else if (editingId) {
        await projectAPI.updateCategory(projectId, editingId, formName.trim(), formColor)
      }
      handleCancel()
      await loadCategories()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save category')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteClick = (category: Category) => {
    setDeleteDialog({ open: true, category })
    setForceDelete(false)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.category) return

    setLoading(true)
    setError(null)
    try {
      const result = await projectAPI.deleteCategory(
        projectId,
        deleteDialog.category.id,
        forceDelete
      )
      setDeleteDialog({ open: false, category: null })
      await loadCategories()
      if (result.annotations_deleted > 0) {
        // Show success message with count
        console.log(`Deleted ${result.annotations_deleted} annotations`)
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to delete category'
      if (detail.includes('annotations')) {
        // Category has annotations - show force delete option
        setError(detail)
        setForceDelete(true)
      } else {
        setError(detail)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Typography variant="h6">
          Categories ({categories.length})
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading && categories.length === 0 ? (
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <>
            <List dense>
              {categories.map((category) => (
                <ListItem
                  key={category.id}
                  secondaryAction={
                    editingId !== category.id && (
                      <Box>
                        <IconButton
                          size="small"
                          onClick={() => handleEdit(category)}
                          disabled={isAdding || editingId !== null}
                        >
                          <Edit fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(category)}
                          disabled={isAdding || editingId !== null}
                        >
                          <Delete fontSize="small" />
                        </IconButton>
                      </Box>
                    )
                  }
                >
                  {editingId === category.id ? (
                    <Box display="flex" alignItems="center" gap={1} width="100%">
                      <Box
                        sx={{
                          width: 24,
                          height: 24,
                          borderRadius: 1,
                          backgroundColor: formColor,
                          cursor: 'pointer',
                          border: '1px solid rgba(0,0,0,0.2)',
                        }}
                        onClick={() => {
                          const currentIndex = PRESET_COLORS.indexOf(formColor)
                          const nextIndex = (currentIndex + 1) % PRESET_COLORS.length
                          setFormColor(PRESET_COLORS[nextIndex])
                        }}
                        title="Click to change color"
                      />
                      <TextField
                        size="small"
                        value={formName}
                        onChange={(e) => setFormName(e.target.value)}
                        placeholder="Category name"
                        sx={{ flex: 1 }}
                        autoFocus
                        onKeyPress={(e) => e.key === 'Enter' && handleSave()}
                      />
                      <IconButton size="small" color="primary" onClick={handleSave}>
                        <Save fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={handleCancel}>
                        <Cancel fontSize="small" />
                      </IconButton>
                    </Box>
                  ) : (
                    <>
                      <Chip
                        size="small"
                        sx={{
                          backgroundColor: category.color,
                          color: '#fff',
                          mr: 1,
                          minWidth: 20,
                          '& .MuiChip-label': { px: 0.5 },
                        }}
                        label=""
                      />
                      <ListItemText primary={category.name} />
                    </>
                  )}
                </ListItem>
              ))}

              {/* Add new category form */}
              {isAdding && (
                <ListItem>
                  <Box display="flex" alignItems="center" gap={1} width="100%">
                    <Box
                      sx={{
                        width: 24,
                        height: 24,
                        borderRadius: 1,
                        backgroundColor: formColor,
                        cursor: 'pointer',
                        border: '1px solid rgba(0,0,0,0.2)',
                      }}
                      onClick={() => {
                        const currentIndex = PRESET_COLORS.indexOf(formColor)
                        const nextIndex = (currentIndex + 1) % PRESET_COLORS.length
                        setFormColor(PRESET_COLORS[nextIndex])
                      }}
                      title="Click to change color"
                    />
                    <TextField
                      size="small"
                      value={formName}
                      onChange={(e) => setFormName(e.target.value)}
                      placeholder="New category name"
                      sx={{ flex: 1 }}
                      autoFocus
                      onKeyPress={(e) => e.key === 'Enter' && handleSave()}
                    />
                    <IconButton size="small" color="primary" onClick={handleSave}>
                      <Save fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={handleCancel}>
                      <Cancel fontSize="small" />
                    </IconButton>
                  </Box>
                </ListItem>
              )}
            </List>

            {!isAdding && editingId === null && (
              <Button
                startIcon={<Add />}
                onClick={handleAdd}
                size="small"
                sx={{ mt: 1 }}
              >
                Add Category
              </Button>
            )}
          </>
        )}

        {/* Delete Confirmation Dialog */}
        <Dialog
          open={deleteDialog.open}
          onClose={() => setDeleteDialog({ open: false, category: null })}
        >
          <DialogTitle>Delete Category</DialogTitle>
          <DialogContent>
            <DialogContentText>
              {forceDelete
                ? `This category has annotations. Deleting it will also delete all associated annotations. Are you sure?`
                : `Are you sure you want to delete "${deleteDialog.category?.name}"?`}
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialog({ open: false, category: null })}>
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              color="error"
              variant={forceDelete ? 'contained' : 'text'}
              disabled={loading}
            >
              {forceDelete ? 'Delete with Annotations' : 'Delete'}
            </Button>
          </DialogActions>
        </Dialog>
      </AccordionDetails>
    </Accordion>
  )
}

export default CategoryManager
