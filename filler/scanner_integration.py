"""
Scanner Integration Module

Handles direct scanning from physical documents using printer/scanner hardware.
Supports multiple scanner types and provides automatic scanner detection.
"""

import os
import subprocess
import tempfile
from typing import List, Optional, Dict, Any
from pathlib import Path
from PIL import Image
import time

try:
    import sane
    SANE_SUPPORT = True
except ImportError:
    SANE_SUPPORT = False

try:
    import win32com.client
    WINDOWS_SCANNER_SUPPORT = True
except ImportError:
    WINDOWS_SCANNER_SUPPORT = False


class ScannerService:
    """Service for direct scanner integration and document scanning."""
    
    def __init__(self, dpi: int = 300, color_mode: str = 'color'):
        """
        Initialize scanner service.
        
        Args:
            dpi: Scanning resolution (default: 300)
            color_mode: Color mode ('color', 'gray', 'lineart')
        """
        self.dpi = dpi
        self.color_mode = color_mode
        self.available_scanners = []
        self._detect_scanners()
    
    def _detect_scanners(self) -> None:
        """Detect available scanners on the system."""
        self.available_scanners = []
        
        # Try SANE (Linux/macOS)
        if SANE_SUPPORT:
            try:
                sane.init()
                devices = sane.get_devices()
                for device in devices:
                    self.available_scanners.append({
                        'name': device[0],
                        'vendor': device[1],
                        'type': 'sane',
                        'description': device[2]
                    })
            except Exception as e:
                print(f"SANE scanner detection failed: {e}")
        
        # Try Windows WIA
        if WINDOWS_SCANNER_SUPPORT:
            try:
                wia = win32com.client.Dispatch('WIA.DeviceManager')
                for device in wia.DeviceInfos:
                    if device.Type == 1:  # Scanner device
                        self.available_scanners.append({
                            'name': device.Properties('Name').Value,
                            'vendor': device.Properties('Manufacturer').Value,
                            'type': 'wia',
                            'description': f"Windows WIA Scanner: {device.Properties('Name').Value}"
                        })
            except Exception as e:
                print(f"Windows WIA scanner detection failed: {e}")
        
        # Try command-line tools
        self._detect_cli_scanners()
    
    def _detect_cli_scanners(self) -> None:
        """Detect scanners using command-line tools."""
        # Try scanimage (SANE command-line)
        try:
            result = subprocess.run(['scanimage', '--list-devices'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'device' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            self.available_scanners.append({
                                'name': parts[1],
                                'vendor': 'Unknown',
                                'type': 'scanimage',
                                'description': line.strip()
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try scanadf (Automatic Document Feeder)
        try:
            result = subprocess.run(['scanadf', '--list-devices'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'device' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            self.available_scanners.append({
                                'name': parts[1],
                                'vendor': 'Unknown',
                                'type': 'scanadf',
                                'description': line.strip()
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def get_available_scanners(self) -> List[Dict[str, Any]]:
        """
        Get list of available scanners.
        
        Returns:
            List[Dict[str, Any]]: List of scanner information
        """
        return self.available_scanners
    
    def scan_document(self, scanner_name: Optional[str] = None, 
                     output_path: Optional[str] = None) -> str:
        """
        Scan a document using the specified or default scanner.
        
        Args:
            scanner_name: Name of scanner to use (optional)
            output_path: Path to save scanned image (optional)
            
        Returns:
            str: Path to scanned image file
            
        Raises:
            RuntimeError: If no scanner is available or scanning fails
        """
        if not self.available_scanners:
            raise RuntimeError("No scanners detected on the system")
        
        # Select scanner
        scanner = None
        if scanner_name:
            for s in self.available_scanners:
                if s['name'] == scanner_name:
                    scanner = s
                    break
            if not scanner:
                raise RuntimeError(f"Scanner '{scanner_name}' not found")
        else:
            scanner = self.available_scanners[0]  # Use first available
        
        # Generate output path if not provided
        if not output_path:
            timestamp = int(time.time())
            output_path = f"input/scanned/scanned_document_{timestamp}.png"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"Scanning with {scanner['name']} ({scanner['type']})...")
        
        # Scan based on scanner type
        if scanner['type'] == 'sane':
            return self._scan_with_sane(scanner, output_path)
        elif scanner['type'] == 'wia':
            return self._scan_with_wia(scanner, output_path)
        elif scanner['type'] in ['scanimage', 'scanadf']:
            return self._scan_with_cli(scanner, output_path)
        else:
            raise RuntimeError(f"Unsupported scanner type: {scanner['type']}")
    
    def _scan_with_sane(self, scanner: Dict[str, Any], output_path: str) -> str:
        """Scan using SANE library."""
        try:
            sane.init()
            device = sane.open(scanner['name'])
            
            # Configure scanner settings
            device.mode = self.color_mode
            device.resolution = self.dpi
            
            # Scan the document
            image = device.scan()
            device.close()
            
            # Save the image
            image.save(output_path)
            print(f"Document scanned successfully: {output_path}")
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"SANE scanning failed: {e}")
    
    def _scan_with_wia(self, scanner: Dict[str, Any], output_path: str) -> str:
        """Scan using Windows WIA."""
        try:
            wia = win32com.client.Dispatch('WIA.DeviceManager')
            device = wia.DeviceInfos(scanner['name']).Connect()
            
            # Get scanner item
            item = device.Items[1]  # Usually the first item is the scanner
            
            # Configure settings
            for prop in item.Properties:
                if prop.Name == 'Horizontal Resolution':
                    prop.Value = self.dpi
                elif prop.Name == 'Vertical Resolution':
                    prop.Value = self.dpi
                elif prop.Name == 'Current Intent':
                    if self.color_mode == 'color':
                        prop.Value = 1
                    elif self.color_mode == 'gray':
                        prop.Value = 2
                    else:
                        prop.Value = 4
            
            # Scan
            image = item.Transfer()
            
            # Save image
            image.SaveFile(output_path)
            print(f"Document scanned successfully: {output_path}")
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"WIA scanning failed: {e}")
    
    def _scan_with_cli(self, scanner: Dict[str, Any], output_path: str) -> str:
        """Scan using command-line tools."""
        try:
            # Use scanimage or scanadf
            cmd = 'scanadf' if scanner['type'] == 'scanadf' else 'scanimage'
            
            # Build command
            command = [
                cmd,
                '--device-name', scanner['name'],
                '--resolution', str(self.dpi),
                '--format', 'png',
                '--output-file', output_path
            ]
            
            # Add color mode
            if self.color_mode == 'gray':
                command.extend(['--mode', 'Gray'])
            elif self.color_mode == 'lineart':
                command.extend(['--mode', 'Lineart'])
            else:
                command.extend(['--mode', 'Color'])
            
            # Execute scan
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise RuntimeError(f"CLI scanning failed: {result.stderr}")
            
            print(f"Document scanned successfully: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Scanning timed out")
        except Exception as e:
            raise RuntimeError(f"CLI scanning failed: {e}")
    
    def scan_multiple_pages(self, scanner_name: Optional[str] = None,
                          output_dir: Optional[str] = None) -> List[str]:
        """
        Scan multiple pages using ADF (Automatic Document Feeder) if available.
        
        Args:
            scanner_name: Name of scanner to use (optional)
            output_dir: Directory to save scanned images (optional)
            
        Returns:
            List[str]: List of paths to scanned image files
        """
        if not output_dir:
            timestamp = int(time.time())
            output_dir = f"input/scanned/multi_page_{timestamp}"
            os.makedirs(output_dir, exist_ok=True)
        
        # Check if scanner supports ADF
        scanner = None
        if scanner_name:
            for s in self.available_scanners:
                if s['name'] == scanner_name:
                    scanner = s
                    break
        
        if not scanner:
            scanner = self.available_scanners[0]
        
        # Try ADF scanning
        if scanner['type'] == 'scanadf':
            return self._scan_multiple_with_adf(scanner, output_dir)
        else:
            # Manual multi-page scanning
            return self._scan_multiple_manual(scanner, output_dir)
    
    def _scan_multiple_with_adf(self, scanner: Dict[str, Any], output_dir: str) -> List[str]:
        """Scan multiple pages using ADF."""
        try:
            command = [
                'scanadf',
                '--device-name', scanner['name'],
                '--resolution', str(self.dpi),
                '--format', 'png',
                '--output-file', f"{output_dir}/page_%d.png"
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise RuntimeError(f"ADF scanning failed: {result.stderr}")
            
            # Get list of generated files
            files = sorted(Path(output_dir).glob("page_*.png"))
            return [str(f) for f in files]
            
        except Exception as e:
            raise RuntimeError(f"ADF scanning failed: {e}")
    
    def _scan_multiple_manual(self, scanner: Dict[str, Any], output_dir: str) -> List[str]:
        """Manual multi-page scanning (prompt user for each page)."""
        files = []
        page_num = 1
        
        while True:
            response = input(f"Place page {page_num} on scanner and press Enter (or 'q' to quit): ")
            if response.lower() == 'q':
                break
            
            output_path = f"{output_dir}/page_{page_num:02d}.png"
            try:
                self.scan_document(scanner['name'], output_path)
                files.append(output_path)
                page_num += 1
            except Exception as e:
                print(f"Scanning failed: {e}")
                break
        
        return files
    
    def test_scanner(self, scanner_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Test scanner functionality.
        
        Args:
            scanner_name: Name of scanner to test (optional)
            
        Returns:
            Dict[str, Any]: Test results
        """
        try:
            if not self.available_scanners:
                return {
                    'status': 'error',
                    'message': 'No scanners detected'
                }
            
            # Use specified scanner or first available
            scanner = None
            if scanner_name:
                for s in self.available_scanners:
                    if s['name'] == scanner_name:
                        scanner = s
                        break
                if not scanner:
                    return {
                        'status': 'error',
                        'message': f"Scanner '{scanner_name}' not found"
                    }
            else:
                scanner = self.available_scanners[0]
            
            # Try to scan a test document
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                test_path = tmp.name
            
            try:
                self.scan_document(scanner['name'], test_path)
                
                # Check if file was created and has content
                if os.path.exists(test_path) and os.path.getsize(test_path) > 0:
                    os.unlink(test_path)  # Clean up
                    return {
                        'status': 'success',
                        'scanner': scanner,
                        'message': 'Scanner test successful'
                    }
                else:
                    return {
                        'status': 'error',
                        'message': 'Scanner produced empty or invalid output'
                    }
            except Exception as e:
                if os.path.exists(test_path):
                    os.unlink(test_path)
                return {
                    'status': 'error',
                    'message': f'Scanner test failed: {str(e)}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Scanner test failed: {str(e)}'
            }
