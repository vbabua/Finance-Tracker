import os

def save_temporary_file(uploaded_file):
    """
    Save the uploaded file to a temporary location.
    """
    # Create a temporary directory if it doesn't exist
    temporary_dir = "temp"
    os.makedirs(temporary_dir, exist_ok=True)

    temporary_file_path = os.path.join(temporary_dir, uploaded_file.name)

    with open(temporary_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return temporary_file_path

def delete_temporary_file(file_path):
    """
    Delete the temporary file after processing.
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print(f"The file {file_path} does not exist.")