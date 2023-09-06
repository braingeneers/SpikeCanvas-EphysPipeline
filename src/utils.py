import braingeneers.utils.s3wrangler as wr
import braingeneers.utils.smart_open_braingeneers as smart_open
from tenacity import retry, stop_after_attempt
import os
@retry(stop=stop_after_attempt(5))
def upload_to_s3(file, s3_path):
    """
    :param file: file content
    :param s3_path:
    :return:
    """
    try:
        with smart_open.open(s3_path, 'w') as f:
            f.write(file)
    except Exception as err:
        print(err)
        return "Uploading file to s3 failed!"

