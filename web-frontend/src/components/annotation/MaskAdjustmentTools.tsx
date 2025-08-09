import React, { useState } from 'react'
import { 
  Box, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  Slider, 
  Button, 
  Typography,
  Grid,
  CircularProgress
} from '@mui/material'
import { maskAPI } from '@/utils/api'

interface MaskAdjustmentToolsProps {
  currentMask: string | null
  onMaskAdjusted: (adjustedMask: string) => void
}

type AdjustmentType = 'expand' | 'contract' | 'smooth'

export const MaskAdjustmentTools: React.FC<MaskAdjustmentToolsProps> = ({
  currentMask,
  onMaskAdjusted
}) => {
  const [adjustmentType, setAdjustmentType] = useState<AdjustmentType>('expand')
  const [adjustmentAmount, setAdjustmentAmount] = useState(5)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleAdjustMask = async () => {
    if (!currentMask) {
      console.error('No mask available for adjustment')
      return
    }

    try {
      setIsProcessing(true)
      
      // Call backend API to adjust mask
      const adjustedMask = await maskAPI.adjustMask(currentMask, adjustmentType, adjustmentAmount)
      onMaskAdjusted(adjustedMask)
      
    } catch (error) {
      console.error('Failed to adjust mask:', error)
      // Could show error toast here
    } finally {
      setIsProcessing(false)
    }
  }

  if (!currentMask) {
    return (
      <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">
          Generate a mask first to use adjustment tools
        </Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Mask Adjustments
      </Typography>
      
      <Grid container spacing={2} alignItems="center">
        <Grid item xs={12} sm={6}>
          <FormControl fullWidth size="small">
            <InputLabel>Adjustment Type</InputLabel>
            <Select
              value={adjustmentType}
              label="Adjustment Type"
              onChange={(e) => setAdjustmentType(e.target.value as AdjustmentType)}
            >
              <MenuItem value="expand">Expand</MenuItem>
              <MenuItem value="contract">Contract</MenuItem>
              <MenuItem value="smooth">Smooth</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} sm={6}>
          <Typography gutterBottom>
            Amount: {adjustmentAmount}
          </Typography>
          <Slider
            value={adjustmentAmount}
            onChange={(_, value) => setAdjustmentAmount(value as number)}
            min={1}
            max={20}
            step={1}
            valueLabelDisplay="auto"
            size="small"
          />
        </Grid>
      </Grid>

      <Box sx={{ mt: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
        <Button
          variant="contained"
          onClick={handleAdjustMask}
          disabled={isProcessing}
          size="small"
        >
          Apply Adjustment
        </Button>
        
        {isProcessing && (
          <>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              Processing...
            </Typography>
          </>
        )}
      </Box>

      <Box sx={{ mt: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {adjustmentType === 'expand' && 'Enlarges the mask boundaries'}
          {adjustmentType === 'contract' && 'Shrinks the mask boundaries'}  
          {adjustmentType === 'smooth' && 'Smooths mask edges and fills holes'}
        </Typography>
      </Box>
    </Box>
  )
}