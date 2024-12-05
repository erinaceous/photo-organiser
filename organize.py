#!/usr/bin/env python3
import argparse
import exiftool
import logging
import ffmpeg
import shutil
import arrow
import glob
import os
import re


IMAGE_PATTERN = r''.join([
    r'(?:',
        r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})',
        r'|',
        r'(?P<epoch>\d{10})',
        r'|',
        r'(?P<epoch_ms>\d{13})',
    r')',
    r'.*',
    r'\.([Jj][Pp][Ee]?[Gg]|[Mm][Pp]4|[Dd][Nn][Gg]|[Aa][Rr][Ww])',
    r'(?:\..*)?',
    r'$'
])


#IMAGE_PATTERN = r'.*(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2}).*\.([Jj][Pp][Ee]?[Gg]|[Mm][Pp]4|[Dd][Nn][Gg])(?:\..*)?$'
#OUTPUT_PATTERN = '{year:04d}/{month:02d}-{month_name}/{day:02d}-{day_name}/{hour:02d}{minute:02d}{second:02d}_{filename}'
OUTPUT_PATTERN = '{year:04d}/{month:02d}-{month_name}/{day:02d}-{day_name}/{filename}'
JPEG_PATTERN = re.compile(r'\.(?P<ext>[Jj][Pp][Ee]?[Gg]|[Mm][Pp]4|[Dd][Nn][Gg]|[Aa][Rr][Ww])$')
EXIF_DATE_PATTERN = re.compile(
    r'(?P<year>\d{4})\:(?P<month>\d{2})\:(?P<day>\d{2})\s+'
    r'(?P<hour>\d{2})\:(?P<minute>\d{2})\:(?P<second>\d{2})'
)


et = exiftool.ExifToolHelper()


def parse_exif(path, input_pattern, output_pattern, timezone):
    match = JPEG_PATTERN.search(path)
    if match is None:
        return None, None
    match_dict = match.groupdict()
    if input_pattern is not None:
        match = input_pattern.search(path)
        if match is None:
            return None, None
        match_dict.update(match.groupdict())
    filename = os.path.basename(path)
    data = {
        'year': 1,
        'month': 1,
        'day': 1,
        'hour': 0,
        'minute': 0,
        'second': 0,
        'epoch': 0,
        'epoch_ms': 0,
        'month_name': 'Unknown',
        'day_name': 'Unknown',
        'filename': filename
    }
    data.update(match_dict)
    ext = data.get('ext', 'jpg').lower().replace('jpeg', 'jpg')
    image_timezone = timezone
    for key in [
        'year', 'month', 'day', 'hour', 'minute', 'second',
        'epoch', 'epoch_ms',
    ]:
        val = data.get(key, None)
        if val is None:
            continue
        data[key] = int(val)
    date = None
    for key in ['epoch', 'epoch_ms']:
        val = data.get(key, None)
        if val is not None:
            date = arrow.get(val).to(image_timezone)
    if date is None:
        date = arrow.get(
            year=data['year'], month=data['month'], day=data['day'],
            hour=data['hour'], minute=data['minute'], second=data['second'],

        ).to(image_timezone)
    if ext in ['jpg', 'dng', 'arw']:
        meta = et.get_metadata(path)
        if len(meta) < 1:
            return None, None
        image = meta[0]
        image_date = None
        for attr in ['EXIF:DateTime', 'EXIF:DateTimeOriginal']:
            if attr in image:
                image_date = EXIF_DATE_PATTERN.search(image.get(attr))
                break
        if image_date is not None:
            data.update(image_date.groupdict())
            for key in [
                'year', 'month', 'day', 'hour', 'minute', 'second',
                'epoch', 'epoch_ms',
            ]:
                val = data.get(key, None)
                if val is None:
                    continue
                data[key] = int(val)
        if timezone == 'offset':
            # weirdly, the .dng files seem to store the offset but the
            # EXIF:DateTime is set to local time, whereas in the jpegs it's
            # set (correctly??) to UTC...
            if ext == 'jpg':
                for attr in ['EXIF:OffsetTime', 'EXIF:OffsetTimeOriginal']:
                    if attr in image:
                        image_timezone = image.get(attr)
                        break
            else:
                image_timezone = 'utc'
        date = arrow.get(
            year=data['year'], month=data['month'], day=data['day'],
            hour=data['hour'], minute=data['minute'], second=data['second']
        ).to(image_timezone)
    elif ext == 'mp4':
        video = ffmpeg.probe(path)
        video_date = None
        if len(video["streams"]) > 0:
            video_date = video["streams"][0]["tags"].get("creation_time")
        if timezone == 'offset':
            image_timezone = 'utc'
        if video_date is not None:
            date = arrow.get(
                video_date
            ).to(image_timezone)
    for key in [
        'year', 'month', 'day', 'hour', 'minute', 'second'
    ]:
        data[key] = getattr(date, key)
    data['month_name'] = date.strftime('%B')
    data['day_name'] = date.strftime('%A')
    return path, output_pattern.format(**data)


def parse_filename(path, input_pattern, output_pattern, timezone):
    if input_pattern is None:
        return None, None
    match = input_pattern.search(path)
    if match is None:
        return None, None
    match_dict = match.groupdict()
    filename = os.path.basename(path)
    data = {
        'year': 1,
        'month': 1,
        'day': 1,
        'hour': 0,
        'minute': 0,
        'second': 0,
        'epoch': 0,
        'epoch_ms': 0,
        'month_name': 'Unknown',
        'day_name': 'Unknown',
        'filename': filename
    }
    data.update(match_dict)
    for key in [
        'year', 'month', 'day', 'hour', 'minute', 'second', 'epoch', 'epoch_ms'
    ]:
        val = data.get(key)
        if val is None:
            continue
        data[key] = int(val)
    if timezone == 'offset':
        timezone = 'utc'
    date = None
    for key in ['epoch', 'epoch_ms']:
        val = data.get(key, 0) or 0
        if val > 0:
            date = arrow.get(val).to(timezone)
    if date is None:
        date = arrow.get(
            year=data['year'], month=data['month'], day=data['day'],
            hour=data['hour'], minute=data['minute'], second=data['second']
        ).to(timezone)
    for key in ['year', 'month', 'day', 'hour', 'minute', 'second']:
        data[key] = getattr(date, key)
    data['month_name'] = date.strftime('%B')
    data['day_name'] = date.strftime('%A')
    return path, output_pattern.format(**data)


def move_file(input_path, output_path, test=False):
    logging.info('%s -> %s', input_path, output_path)
    if test is True:
        return
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    return shutil.move(input_path, output_path)


def move_files(input_path, output_path, linked_files=False, test=False):
    input_without_ext = os.path.splitext(input_path)[0]
    output_without_ext = os.path.splitext(output_path)[0]
    if linked_files is True:
        paths = glob.glob(f'{input_without_ext}*')
    else:
        paths = [input_path]
    for path in paths:
        path_and_ext = os.path.splitext(path)
        move_file(
            input_path=path,
            output_path=f'{output_without_ext}{path_and_ext[-1]}',
            test=test
        )


def walk_directory(
    start, output_directory,
    input_pattern, output_pattern,
    max_depth=None, use_exif=False,
    timezone='utc'
):
    """
    Use os.walk to walk a directory structure yielding absolute paths which
    match the regular expression pattern.
    """
    for root, dirs, files in os.walk(start, topdown=True):
        if max_depth is not None:
            depth = len(root.rpartition(start)[-1].split(os.sep)) - 1
            if depth > max_depth:
                continue
        for path in files:
            try:
                input_path, output_path = None, None
                if use_exif is True:
                    input_path, output_path = parse_exif(
                        path=os.path.join(start, root, path),
                        input_pattern=input_pattern,
                        output_pattern=output_pattern,
                        timezone=timezone
                    )
                else:
                    input_path, output_path = parse_filename(
                        path=os.path.join(start, root, path),
                        input_pattern=input_pattern,
                        output_pattern=output_pattern,
                        timezone=timezone
                    )
                if input_path is None or output_path is None:
                    continue
            except BaseException as e:
                logging.exception(
                    'error with %s', input_path
                )
                continue
            output_path = os.path.join(output_directory, output_path)
            yield input_path, output_path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--output-directory', default=os.getcwd()
    )
    parser.add_argument(
        '-t', '--test', action='store_true', default=False
    )
    parser.add_argument(
        '-d', '--max-depth', type=int, default=None
    )
    parser.add_argument(
        '-f', '--filename-pattern', default=IMAGE_PATTERN
    )
    parser.add_argument(
        '-p', '--output-pattern', default=OUTPUT_PATTERN
    )
    parser.add_argument(
        '-e', '--use-exif', default=False, action='store_true'
    )
    parser.add_argument(
        '-l', '--linked-files', default=False, action='store_true'
    )
    parser.add_argument(
        '-z', '--timezone', default='utc'
    )
    parser.add_argument(
        'input_directories', nargs='*', default=None
    )
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    input_pattern = None
    if args.filename_pattern not in ['', None]:
        input_pattern = re.compile(args.filename_pattern)
    output_pattern = args.output_pattern
    input_directories = args.input_directories or [os.getcwd()]
    linked_files = args.linked_files or []
    timezone = args.timezone
    for input_directory in input_directories:
        for input_path, output_path in walk_directory(
            start=input_directory,
            output_directory=args.output_directory,
            input_pattern=input_pattern,
            output_pattern=output_pattern,
            max_depth=args.max_depth,
            use_exif=args.use_exif,
            timezone=timezone
        ):
            move_files(
                input_path=input_path,
                output_path=output_path,
                linked_files=linked_files,
                test=args.test
            )


if __name__ == '__main__':
    main()
