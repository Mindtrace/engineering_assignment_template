import os
import zipfile
import tarfile
from tqdm import tqdm
from urllib.request import urlretrieve


def tqdm_hook(t):
    """Wraps tqdm instance into a callback hook, suitable for passing to urllib.request.urlretrieve.

    Remember to call close() or __exit__() on the tqdm instance once you're done with it. Most simply use tqdm as a
    context manager (refer to the example below).

    Returns:
        A callback function suitable for passing as `reporthook` to urllib.request.urlretrieve.

    Example::

        import os
        from tqdm import tqdm
        from urllib.request import urlretrieve
        from mtrix import Config
        from mtrix.utils.downloads import tqdm_hook

        url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"  # Meta's 2.6gb SegmentAnything model
        save_path = os.path.join(Config()["DIR_MODELS"]["SAM"], "sam_vit_h_4b8939.pth")

        with tqdm(desc="Downloading SAM (vit_h) model") as t:
            reporthook = tqdm_hook(t)
            urlretrieve(url, save_path, reporthook=reporthook)
    """
    last_b = [0]

    def update_to(b: int = 1, bsize: int = 1, tsize: int | None = None):
        """Update the progress bar.

        Args:
            b: Number of blocks transferred so far [default: 1].
            bsize: Size of each block (in tqdm units) [default: 1].
            tsize: Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            t.total = tsize
        t.update((b - last_b[0]) * bsize)
        last_b[0] = b

    return update_to


def download_url(url: str, save_path: str, progress_bar: bool = True, desc: str = "Downloading file"):
    """Download a file from a URL to a specified path.

    Args:
        url: The URL to download the file from.
        save_path: The path to save the downloaded file to.
        progress_bar: Whether to display a progress bar during download.
        desc: Description to display in the progress bar.

    Example::

        import os
        from mtrix import Config
        from mtrix.utils import download_url

        url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"  # Meta's 2.6gb SegmentAnything model
        save_path = os.path.join(Config()["DIR_MODELS"]["SAM"], "sam_vit_h_4b8939.pth")

        download_url(url, save_path, progress_bar=True, desc="Downloading SAM (vit_h) model")

    """
    if progress_bar:
        with tqdm(desc=desc) as t:
            reporthook = tqdm_hook(t)
            _ = urlretrieve(url, save_path, reporthook=reporthook)
    else:
        _ = urlretrieve(url, save_path)


def download_and_extract_tarball(url: str, save_dir: str, progress_bar: bool = True, desc: str = "Downloading file") -> str:
    """Download a tarball file from a URL and extract it to a specified directory.

    Args:
        url: The URL to download the file from.
        save_dir: The directory to save the unzipped file to.
        progress_bar: Whether to display a progress bar during download.
        desc: Description to display in the progress bar.

    Returns:
        str: Path to the extracted folder
    """
    os.makedirs(save_dir, exist_ok=True)
    temp_path = os.path.join(save_dir, "temp_file.tgz")
    download_url(url=url, save_path=temp_path, progress_bar=progress_bar, desc=desc)
    
    tarfile_ = tarfile.open(temp_path, "r")
    # Get the common prefix path of all files in the archive
    members = tarfile_.getmembers()
    extracted_dir = os.path.join(save_dir, os.path.commonpath([m.name for m in members]))
    
    tarfile_.extractall(save_dir)
    tarfile_.close()
    os.remove(temp_path)
    return extracted_dir


def download_and_extract_zip(url: str, save_dir: str, progress_bar: bool = True, desc: str = "Downloading file") -> str:
    """Download a zip file from a URL and extract it to a specified directory.

    Args:
        url: The URL to download the file from.
        save_dir: The directory to save the unzipped file to.
        progress_bar: Whether to display a progress bar during download.
        desc: Description to display in the progress bar.
        
    Returns:
        str: Path to the extracted folder
    """
    os.makedirs(save_dir, exist_ok=True)
    temp_path = os.path.join(save_dir, "temp_file.zip")
    download_url(url=url, save_path=temp_path, progress_bar=progress_bar, desc=desc)
    
    with zipfile.ZipFile(temp_path, "r") as zip_ref:
        # Get the common prefix path of all files in the archive
        members = zip_ref.namelist()
        extracted_dir = os.path.join(save_dir, os.path.commonpath(members))
        zip_ref.extractall(save_dir)
        
    os.remove(temp_path)
    print(f"Extracted zip to {extracted_dir}")
    return extracted_dir
