from src.services.drive_folder_manager import DriveFolderManager
from uuid import uuid4
import asyncio

async def test_drive_folders():
    drive_manager = DriveFolderManager()

    # Test folder structure creation
    result = await drive_manager.create_assessment_folder_structure(
        workflow_id=uuid4(),
        certification_name="AWS Test Certification",
        user_id="test@example.com"
    )

    print(f"Folder creation: {result['success']}")
    if result['success']:
        print(f"Main folder: {result['folder_structure']['main_folder_name']}")

    return result

# Run the test
result = asyncio.run(test_drive_folders())
