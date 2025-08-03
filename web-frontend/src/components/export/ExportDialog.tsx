// web-frontend/src/components/export/ExportDialog.tsx
/**
 * Export Dialog Component - Following Streamlit prototype patterns
 * Extensible design for multiple export formats
 */
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Checkbox,
  FormControlLabel,
  Box,
  Alert,
  CircularProgress,
  Typography,
  Divider,
  Card,
  CardContent
} from '@mui/material';
import { Download, FileDownload, Check, Error } from '@mui/icons-material';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: number;
  videoId?: number;
  projectName?: string;
}

interface ExportFormat {
  name: string;
  description: string;
  fileExtension: string;
}

interface ExportOptions {
  includeImages?: boolean;
  exportMasks?: boolean;
  [key: string]: any;
}

interface ExportResult {
  success: boolean;
  exported_path: string;
  format: string;
  download_url: string;
}

const ExportDialog: React.FC<ExportDialogProps> = ({
  open,
  onClose,
  projectId,
  videoId,
  projectName = 'project'
}) => {
  // State management (following Streamlit patterns)
  const [selectedFormat, setSelectedFormat] = useState<string>('COCO');
  const [supportedFormats, setSupportedFormats] = useState<string[]>([]);
  const [exportOptions, setExportOptions] = useState<ExportOptions>({});
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Format descriptions (following Streamlit prototype info)
  const formatDescriptions: Record<string, ExportFormat> = {
    'COCO': {
      name: 'COCO',
      description: 'Common Objects in Context format - JSON with polygon annotations',
      fileExtension: '.json'
    },
    'YOLO': {
      name: 'YOLO',
      description: 'YOLO format - Text files with normalized polygon coordinates',
      fileExtension: '.txt + classes.txt'
    }
  };

  // Load supported formats on component mount
  useEffect(() => {
    if (open) {
      fetchSupportedFormats();
      setExportResult(null);
      setError(null);
    }
  }, [open]);

  const fetchSupportedFormats = async () => {
    try {
      const response = await fetch('/api/v1/export/formats');
      const data = await response.json();
      
      if (data.success) {
        setSupportedFormats(data.formats);
        if (data.formats.length > 0 && !data.formats.includes(selectedFormat)) {
          setSelectedFormat(data.formats[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch supported formats:', err);
      setError('Failed to load export formats');
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);
    setExportResult(null);

    try {
      const url = `/api/v1/export/project/${projectId}?format=${selectedFormat}${videoId ? `&video_id=${videoId}` : ''}`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Export failed');
      }

      if (data.success) {
        setExportResult(data);
      } else {
        throw new Error('Export failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Export failed';
      setError(errorMessage);
      console.error('Export error:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownload = () => {
    if (exportResult?.download_url) {
      // Create download link
      const downloadUrl = `/api/v1${exportResult.download_url}`;
      window.open(downloadUrl, '_blank');
    }
  };

  const handleFormatChange = (format: string) => {
    setSelectedFormat(format);
    
    // Reset format-specific options (following Streamlit patterns)
    const newOptions: ExportOptions = {};
    
    if (format === 'COCO') {
      newOptions.includeImages = true;
    } else if (format === 'YOLO') {
      newOptions.exportMasks = true;
    }
    
    setExportOptions(newOptions);
  };

  const handleOptionChange = (option: string, value: any) => {
    setExportOptions(prev => ({
      ...prev,
      [option]: value
    }));
  };

  const renderFormatOptions = () => {
    const formatInfo = formatDescriptions[selectedFormat];
    if (!formatInfo) return null;

    return (
      <Card variant="outlined" sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {formatInfo.name} Format Options
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            {formatInfo.description}
          </Typography>

          {selectedFormat === 'COCO' && (
            <FormControlLabel
              control={
                <Checkbox
                  checked={exportOptions.includeImages || false}
                  onChange={(e) => handleOptionChange('includeImages', e.target.checked)}
                />
              }
              label="Include Frame Images"
            />
          )}

          {selectedFormat === 'YOLO' && (
            <>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={exportOptions.exportMasks || false}
                    onChange={(e) => handleOptionChange('exportMasks', e.target.checked)}
                  />
                }
                label="Export Segmentation Masks"
              />
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                YOLO format supports both bounding boxes and polygon segmentation.
              </Typography>
            </>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderExportStatus = () => {
    if (exportResult) {
      return (
        <Alert severity="success" icon={<Check />} sx={{ mt: 2 }}>
          <Typography variant="body1">
            Export completed successfully!
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Format: {exportResult.format} • Path: {exportResult.exported_path}
          </Typography>
          <Box sx={{ mt: 1 }}>
            <Button
              variant="contained"
              color="success"
              startIcon={<FileDownload />}
              onClick={handleDownload}
            >
              Download Export
            </Button>
          </Box>
        </Alert>
      );
    }

    if (error) {
      return (
        <Alert severity="error" icon={<Error />} sx={{ mt: 2 }}>
          <Typography variant="body1">Export Failed</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
      );
    }

    return null;
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="md" 
      fullWidth
      PaperProps={{
        sx: { minHeight: '400px' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center">
          <Download sx={{ mr: 1 }} />
          Export Annotations
        </Box>
        <Typography variant="body2" color="textSecondary">
          Project: {projectName} {videoId && `• Video ID: ${videoId}`}
        </Typography>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Format Selection */}
          <FormControl fullWidth>
            <InputLabel>Export Format</InputLabel>
            <Select
              value={selectedFormat}
              label="Export Format"
              onChange={(e) => handleFormatChange(e.target.value)}
              disabled={isExporting}
            >
              {supportedFormats.map((format) => (
                <MenuItem key={format} value={format}>
                  {format} - {formatDescriptions[format]?.fileExtension || format}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Format-specific Options */}
          {renderFormatOptions()}

          {/* Export Status */}
          {renderExportStatus()}

          <Divider />

          {/* Export Info */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Export Information
            </Typography>
            <Typography variant="body2" color="textSecondary">
              • Annotations will be exported in the selected format
              • Coordinates will be properly scaled for the target format
              • Only frames with annotations will be included
              • Export files will be available for download after processing
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button 
          onClick={onClose} 
          disabled={isExporting}
        >
          {exportResult ? 'Close' : 'Cancel'}
        </Button>
        <Button
          onClick={handleExport}
          variant="contained"
          disabled={isExporting || supportedFormats.length === 0}
          startIcon={isExporting ? <CircularProgress size={16} /> : <Download />}
        >
          {isExporting ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExportDialog;