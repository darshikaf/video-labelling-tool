class AnnotationTools:
    def __init__(self):
        """Initialize the annotation tools"""
        self.current_tool = "point"  # Default tool
        self.point_mode = "positive"  # Default to positive points
        
    def set_tool(self, tool_name):
        """
        Set the current tool
        
        Args:
            tool_name (str): Tool name (point, box, etc.)
        """
        self.current_tool = tool_name
        
    def set_point_mode(self, mode):
        """
        Set the point mode
        
        Args:
            mode (str): 'positive' or 'negative'
        """
        if mode in ["positive", "negative"]:
            self.point_mode = mode
            
    def get_current_tool(self):
        """Get the current tool configuration"""
        return {
            "tool": self.current_tool,
            "point_mode": self.point_mode if self.current_tool == "point" else None
        }
