import habit_engine
from datetime import datetime

def test_init_constants():
    assert habit_engine.__version__ == "2.2.0"
    assert habit_engine.__author__ == "Herald Inyang"
    assert habit_engine.__description__ == "A modern Python application for tracking daily habits and maintaining streaks, featuring both CLI and GUI interfaces."
    assert habit_engine.__app_name__ == "HERALDEXX HABIT TRACKER"
    assert habit_engine.__copyright__ == f"Copyright © {datetime.now().year} Herald Inyang"
    assert habit_engine.__license__ == "MIT"
    assert habit_engine.__website__ == "https://github.com/heraldexx"
    assert habit_engine.__release_date__ == "2025-06-12"
    
    assert "MIT License" in habit_engine.__license_text__
    assert "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM" in habit_engine.__license_text__
    
    assert "Modern, customizable interface with Dark/Light/System themes" in habit_engine.__gui_features__
    assert "Visualization/Chart customization" in habit_engine.__gui_features__
    assert len(habit_engine.__gui_features__) == 11
    
    assert "Track 2-10 daily habits" in habit_engine.__cli_features__
    assert "Visualization plot generation" in habit_engine.__cli_features__
    assert len(habit_engine.__cli_features__) == 8
    
    assert habit_engine.__features__ == habit_engine.__gui_features__ + habit_engine.__cli_features__
    
    assert "Herald Inyang (Lead Developer)" in habit_engine.__credits__
    assert "Adesua Ayomitan (Project Supervisor)" in habit_engine.__credits__
    assert len(habit_engine.__credits__) == 3
