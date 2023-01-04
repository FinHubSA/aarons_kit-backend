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
    path("api/articles", views.get_articles, name="get_articles"),
    path("api/authors", views.get_authors, name="get_authors"),
    path("api/issues", views.get_issues, name="get_issues"),
    path("api/journals", views.get_journals, name="get_journals"),
    path("api/articles/pdf",views.store_pdf,name="store_pdf"),
    path("api/accounts",views.get_accounts,name="get_accounts"),
    path("api/accounts/amount/for-distribution",views.get_amount_for_distribution,name="get_amount_for_distribution"),
    path("api/accounts/amount/distributed-todate",views.get_amount_distributed_todate,name="get_amount_distributed_todate"),
    path("api/articles/update/bucketurl",views.update_article_bucket_url,name="update_article_bucket_url"),
]
