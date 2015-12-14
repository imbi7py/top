# -*- coding: utf-8 -*-
import os
import time
import codecs
import argparse
from json import load
from os import listdir
from email.Utils import formatdate
from os.path import join as pjoin, isdir, isfile, dirname
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthcalendar, month_name

import ashes
from boltons.fileutils import mkdir_p
from boltons.timeutils import UTC, isoparse

from common import (DATA_PATH_TMPL,
                    TEMPLATE_PATH,
                    FEED_PATH_TMPL,
                    LANG_PROJ_LINK_TMPL,
                    DEFAULT_LANG,
                    BASE_PATH,
                    LOCAL_LANG_MAP,
                    DEFAULT_PROJECT,
                    ABOUT)

ABOUT_PATH = pjoin(BASE_PATH, 'about.html')
INDEX_PATH = pjoin(BASE_PATH, '')
HTML_FILE_TMPL = '{lang}/{project}/{year}/{month}/{day}.html'
HTML_PATH_TMPL = pjoin(BASE_PATH, HTML_FILE_TMPL)
MONTH_INDEX = '{lang}/{project}/{year}/{month}/'
MONTH_INDEX_PATH = pjoin(BASE_PATH, MONTH_INDEX)
YEAR_PATH = pjoin(BASE_PATH, '{lang}/{project}/{year}')
YEAR_INDEX_PATH = pjoin(BASE_PATH, '{lang}/{project}/{year}/')
PROJECT_PATH = pjoin(BASE_PATH, '{lang}/{project}')
PROJECT_INDEX_PATH = pjoin(BASE_PATH, '{lang}/{project}/')
LANG_PATH = pjoin(BASE_PATH, '{lang}')
LANG_INDEX_PATH = pjoin(BASE_PATH, '{lang}/')

DEFAULT_TEMPLATE_NAME = 'chart.dust'
ABOUT_TEMPLATE = 'about.dust'
MONTH_INDEX_TMPL = 'month_index.dust'
YEAR_INDEX_TMPL = 'year_index.dust'
PROJECT_INDEX_TMPL = 'project_index.dust'
GENERIC_INDEX_TMPL = 'index.dust'
MOST_RECENT_CHART = date.today() - timedelta(days=1)


ASHES_ENV = None


def save_rendered(outfile_name, template_name, context):
    global ASHES_ENV  # retain laziness
    if not ASHES_ENV:
        ASHES_ENV = ashes.AshesEnv([TEMPLATE_PATH], keep_whitespace=True)
    rendered = ASHES_ENV.render(template_name, context)
    try:
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    except IOError:
        mkdir_p(dirname(outfile_name))
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    with out_file:
        out_file.write(rendered)
    print 'successfully generated %s' % outfile_name


def check_most_recent(lang=DEFAULT_LANG, project=DEFAULT_PROJECT):
    sdir = pjoin(BASE_PATH, lang, project)
    recent_year = max([f for f in listdir(sdir) if isdir(pjoin(sdir, f))])
    sdir = pjoin(sdir, recent_year)
    recent_month = max([f for f in listdir(sdir) if isdir(pjoin(sdir, f))])
    sdir = pjoin(sdir, recent_month)
    try:
        recent_day = max([int(f.replace('.json', ''))
                          for f
                          in listdir(sdir) if '.json' in f])
    except ValueError as e:
        pass  # import pdb; pdb.set_trace()
    return date(year=int(recent_year),
                month=int(recent_month),
                day=int(recent_day))


def check_projects():
    ret = {}
    for lang in LOCAL_LANG_MAP.keys():
        lang_dir = pjoin(BASE_PATH, lang)
        if isdir(lang_dir):
            projects = [f for f
                        in listdir(lang_dir)
                        if not f.startswith('.')
                        and isdir(pjoin(lang_dir, f))]
            ret[lang] = projects
    return ret


def check_chart(cur_date, days, lang, project):
    query_date = cur_date - timedelta(days=days)
    filename = HTML_PATH_TMPL.format(lang=lang,
                                     project=project,
                                     year=query_date.year,
                                     month=query_date.month,
                                     day=query_date.day)
    if isfile(filename):
        return HTML_FILE_TMPL.format(lang=lang,
                                     project=project,
                                     year=query_date.year,
                                     month=query_date.month,
                                     day=query_date.day)
    return None


def check_month(cur_date, months, lang, project):
    query_date = cur_date - relativedelta(months=months)
    dirname = MONTH_INDEX_PATH.format(lang=lang,
                                      project=project,
                                      year=query_date.year,
                                      month=query_date.month)
    if isdir(dirname):
        return MONTH_INDEX.format(lang=lang,
                                  project=project,
                                  year=query_date.year,
                                  month=query_date.month)
    return None


def load_data(query_date, lang, project):
    file_name = DATA_PATH_TMPL.format(lang=lang,
                                      project=project,
                                      year=query_date.year,
                                      month=query_date.month,
                                      day=query_date.day)
    with open(file_name, 'r') as data_file:
        data = load(data_file)
    return data


def save_chart(query_date, lang, project):
    data = load_data(query_date, lang, project)
    data['current'] = HTML_FILE_TMPL.format(lang=lang,
                                            project=project,
                                            year=query_date.year,
                                            month=query_date.month,
                                            day=query_date.day)
    #TODO: Shouldn't need to format HTML_FILE_TMPL and HTML_PATH_TMPL
    data['prev'] = check_chart(query_date, 1, lang, project)
    data['next'] = check_chart(query_date, -1, lang, project)
    data['about'] = ABOUT
    data['dir_depth'] = '../' * 4
    data['is_index'] = False
    data['project_lower'] = project
    data.setdefault('meta', {})['generated'] = datetime.utcnow().isoformat()

    outfile_name = HTML_PATH_TMPL.format(lang=lang,
                                         project=project,
                                         year=query_date.year,
                                         month=query_date.month,
                                         day=query_date.day)
    save_rendered(outfile_name, DEFAULT_TEMPLATE_NAME, data)
    most_recent = check_most_recent(lang=lang, project=project)
    if query_date == most_recent:
        lang_index_path = LANG_INDEX_PATH.format(lang=lang)
        lang_index = pjoin(lang_index_path, 'index.html')
        data['dir_depth'] = '../'
        data['is_index'] = True
        save_rendered(lang_index, DEFAULT_TEMPLATE_NAME, data)
        if lang == DEFAULT_LANG and project == DEFAULT_PROJECT:
            main_index = pjoin(INDEX_PATH, 'index.html')
            data['dir_depth'] = ''
            data['is_index'] = True
            save_rendered(main_index, DEFAULT_TEMPLATE_NAME, data)


def update_charts(cur_date, lang, project):
    # Update the current chart
    save_chart(cur_date, lang, project)
    # Update the prev and next charts (for navigation)
    if check_chart(cur_date, 1, lang, project):
        prev_date = cur_date - timedelta(days=1)
        save_chart(prev_date, lang, project)
    if check_chart(cur_date, -1, lang, project):
        next_date = cur_date + timedelta(days=1)
        save_chart(next_date, lang, project)
    # Update the feed
    update_feeds(cur_date, lang, project)
    # Update the monthly and yearly navigation
    update_month(cur_date, lang, project)
    prev_month = cur_date - relativedelta(months=1)
    update_month(prev_month, lang, project)
    update_year(cur_date.year, lang, project)
    update_project(lang, project)
    return 'Saved and updated'


def to_rss_timestamp(dt_obj, to_utc=False):
    if to_utc and dt_obj.tzinfo:
        dt_obj = dt_obj.astimezone(UTC)
    return formatdate(time.mktime(dt_obj.timetuple()))


def update_feeds(cur_date, lang, project, day_count=10):
    canonical_url = LANG_PROJ_LINK_TMPL.format(lang=lang, project=project)
    render_ctx = {'lang_code': lang,
                  'lang_name': LOCAL_LANG_MAP[lang],
                  'project': project.title(),
                  'canonical_url': canonical_url,
                  'cur_utc': to_rss_timestamp(datetime.now())}

    data_list = []
    for day_delta in range(0, day_count):
        date_i = cur_date - timedelta(days=day_delta)
        try:
            date_i_data = load_data(date_i, lang, project)
        except IOError:
            print 'no data found for %r' % date_i
            continue

        # utc_pub_dt = isoparse(date_i_data['meta']['generated'])
        midnight_utc = datetime.utcfromtimestamp(0).timetz()
        pub_dt = datetime.combine(date_i, midnight_utc)
        date_i_data['pub_timestamp'] = to_rss_timestamp(pub_dt)
        date_i_data['summary'] = ASHES_ENV.render('summary.html', date_i_data)
        data_list.append(date_i_data)
    render_ctx['entries'] = data_list
    feed_path = FEED_PATH_TMPL.format(lang=lang, project=project)
    save_rendered(feed_path, 'rss.xml', render_ctx)
    return


def list_feeds():
    FEED_INDEX = pjoin(BASE_PATH, 'feeds')
    fdir = FEED_INDEX
    feeds = [{'name': LOCAL_LANG_MAP[f[:2]], 'url': 'feeds/%s' % f}
             for f
             in listdir(fdir)
             if '.rss' in f]
    return feeds


def update_about():
    project_map = check_projects()
    langs = project_map.keys()
    feeds = list_feeds()
    data = {'languages': [],
            'about': ABOUT,
            'feeds': feeds,
            'meta': {'generated': datetime.utcnow().isoformat()}}
    for lang in langs:
        lang_name = LOCAL_LANG_MAP[lang]
        for project in project_map[lang]:
            data['languages'].append({'name': lang_name,
                                      'url': '%s/' % (lang,)})
            # TODO: Add template support for projects other than Wikipedia
            # update_lang(lang, project)
    save_rendered(ABOUT_PATH, ABOUT_TEMPLATE, data)


def monthly_calendar(year, month, lang, project):
    ret = []
    weeks = monthcalendar(year, month)
    for week in weeks:
        ret_week = {'days': []}
        for day in week:
            chart = None
            if day > 0:
                filename = HTML_PATH_TMPL.format(lang=lang,
                                                 project=project,
                                                 year=year,
                                                 month=month,
                                                 day=day)
                if isfile(filename):
                    chart = True
            ret_week['days'].append({'year': year,
                                     'month': month,
                                     'day': day,
                                     'lang': lang,
                                     'project': project,
                                     'chart': chart})
        ret.append(ret_week)
    return ret


def yearly_calendar(year, lang, project):
    ret = []
    year_path = YEAR_PATH.format(year=year,
                                 lang=lang,
                                 project=project)
    for month in next(os.walk(year_path))[1]:
        month = int(month)
        mname = month_name[month]
        mdata = {'month_name': mname,
                 'month': month,
                 'year': year}
        mdata['dates'] = monthly_calendar(year, month, lang, project)
        ret.append(mdata)
    ret.reverse()
    return ret


def update_month(query_date, lang, project):
    year = query_date.year
    month = query_date.month
    data = {'dir_depth': '../' * 4,
            'month_name': month_name[month],
            'project': project.capitalize(),
            'full_lang': LOCAL_LANG_MAP[lang],
            'prev_month': check_month(query_date, 1, lang, project),
            'next_month': check_month(query_date, -1, lang, project),
            'year': year,
            'about': ABOUT,
            'meta': {'generated': datetime.utcnow().isoformat()}}
    data['dates'] = monthly_calendar(year, month, lang, project)
    month_index_path = MONTH_INDEX_PATH.format(lang=lang,
                                               project=project,
                                               year=year,
                                               month=month)
    month_index = pjoin(month_index_path, 'index.html')
    save_rendered(month_index, MONTH_INDEX_TMPL, data)
    return data


def update_year(year, lang, project):
    full_lang = LOCAL_LANG_MAP[lang]
    year_data = {'months': [],
                 'year': year,
                 'project': project.capitalize(),
                 'full_lang': full_lang,
                 'dir_depth': '../' * 3,
                 'about': ABOUT}
    year_data['months'] = yearly_calendar(year, lang, project)
    year_index_path = YEAR_INDEX_PATH.format(year=year,
                                             lang=lang,
                                             project=project)
    year_index = pjoin(year_index_path, 'index.html')
    save_rendered(year_index, YEAR_INDEX_TMPL, year_data)


def update_project(lang, project):
    full_lang = LOCAL_LANG_MAP[lang]
    data = {'years': [],
            'project': project.capitalize(),
            'full_lang': full_lang,
            'dir_depth': '../' * 2,
            'about': ABOUT}
    project_path = PROJECT_PATH.format(lang=lang,
                                       project=project)
    project_index = pjoin(project_path, 'index.html')
    for year in [y for y in next(os.walk(project_path))[1]]:
        year = int(year)
        year_data = yearly_calendar(year, lang, project)
        data['years'] += year_data
    save_rendered(project_index, PROJECT_INDEX_TMPL, data)


def update_lang(lang, project):
    # NOTE: the lang index is now a copy of the most recent chart
    full_lang = LOCAL_LANG_MAP[lang]
    lang_path = LANG_PATH.format(lang=lang)
    lang_data = {'projects': [p.capitalize()
                              for p
                              in next(os.walk(lang_path))[1]],
                 'project': project.capitalize(),
                 'full_lang': full_lang,
                 'dir_depth': '../',
                 'about': ABOUT}
    lang_index_path = LANG_INDEX_PATH.format(lang=lang)
    lang_index = pjoin(lang_index_path, 'index.html')
    save_rendered(lang_index, GENERIC_INDEX_TMPL, lang_data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    parser.add_argument('--lang', default=DEFAULT_LANG)
    parser.add_argument('--project', default=DEFAULT_PROJECT)
    parser.add_argument('--meta', '-m', action='store_true')
    args = parser.parse_args()
    if args.meta:
        update_about()
    else:
        if not args.date:
            input_date = MOST_RECENT_CHART
        else:
            input_date = datetime.strptime(args.date, '%Y%m%d').date()
        update_charts(input_date, args.lang, args.project)
        update_feeds(input_date, args.lang, args.project)
