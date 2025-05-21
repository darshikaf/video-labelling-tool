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
    
    def process_prompt(self, tool_config, sam_model, image, points=None, boxes=None):
        """
        Process annotation prompt with the current tool
        
        Args:
            tool_config (dict): Tool configuration
            sam_model: SAM model instance
            image: Input image
            points: List of point coordinates
            boxes: List of box coordinates
            
        Returns:
            numpy.ndarray: Segmentation mask
        """
        if tool_config["tool"] == "point" and points:
            is_positive = tool_config["point_mode"] == "positive"
            point_prompts = [(x, y, is_positive) for x, y in points]
            return sam_model.predict(image, prompt_type="point", points=point_prompts)
            
        elif tool_config["tool"] == "box" and boxes:
            return sam_model.predict(image, prompt_type="box", boxes=boxes)
            
        return None
