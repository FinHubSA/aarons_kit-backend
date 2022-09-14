# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.urls import path

from . import views

urlpatterns = [
    path(
        "api/articles/metadata",
        views.store_metadata,
        name="store_metadata",
    ),
    path("api/articles", views.get_all_articles, name="get_all_articles"),
    path("api/articles/title", views.get_article_by_title, name="get_article_by_title"),
    path(
        "api/articles/author",
        views.get_articles_by_author,
        name="get_articles_by_author",
    ),
    path(
        "api/articles/journal",
        views.get_articles_from_journal,
        name="get_articles_from_journal",
    ),
    path(
        "api/journals/titles",
        views.get_all_journals,
        name="get_all_journals",
    ),
]
