import datetime
import os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
import requests
from freezegun import freeze_time

from exceptions import ApiError
from script import PullRequestsData


class TestListPullRequests:
    @pytest.fixture
    def pull_requests_data(self):
        return PullRequestsData(repo_owner="startstopstep", repo_name="test-repo")

    @pytest.fixture
    def pr_response_data(self):
        return [{
            "number": 1,
            "title": "Title 1",
            "user": {
                "login": "user1"
            },
            "created_at": "2021-01-01T10:00:00Z",
            "updated_at": "2021-01-01T10:00:00Z",
            "commits_url": "commits_url_1",
            "comments_url": "comments_url_1",
            "requested_reviewers": [
                {
                    "login": "reviewer1",
                    "id": 1,
                    "type": "User"
                }
            ]
        }, {
            "number": 2,
            "title": "Title 2",
            "user": {
                "login": "user2"
            },
            "created_at": "2021-01-02T10:00:00Z",
            "updated_at": "2021-01-02T10:00:00Z",
            "commits_url": "commits_url_2",
            "comments_url": "comments_url_2",
            "requested_reviewers": [
                {
                    "login": "reviewer2",
                    "id": 2,
                    "type": "User"
                }
            ]
        }]

    @pytest.fixture
    def mock_pull_requests(self, monkeypatch):
        def mock_list_pull_requests(*args):
            return [
                (1, "Title 1", "Author 1", "2022-01-01T00:00:00Z", "2022-01-02T00:00:00Z", 1, 1, 1, ["Reviewer 1"]),
                (2, "Title 2", "Author 2", "2022-02-01T00:00:00Z", "2022-02-02T00:00:00Z", 2, 2, 2, ["Reviewer 2"])
            ]

        monkeypatch.setattr('script.PullRequestsData.list_pull_requests', mock_list_pull_requests)

    def test_initialized_with_correct_attributes(self, pull_requests_data):
        assert pull_requests_data.repo_owner == "startstopstep"
        assert pull_requests_data.repo_name == "test-repo"

    def test_make_request_success(self, pull_requests_data):
        url = "https://api.github.com/repos/startstopstep/test-repo/pulls"
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = [{'test_key': 'test_value'}]
        with patch.object(requests, 'get', return_value=response) as mock_get:
            result = pull_requests_data.make_request(url)

        mock_get.assert_called_once_with(url)
        assert result == [{'test_key': 'test_value'}]

    def test_make_request_failure(self, pull_requests_data):
        url = "https://api.github.com/repos/startstopstep/test-repo/pulls"
        response = MagicMock()
        response.status_code = 400
        with patch.object(requests, 'get', return_value=response) as mock_get:
            with pytest.raises(ApiError) as error:
                pull_requests_data.make_request(url)

        mock_get.assert_called_once_with(url)
        assert str(error.value) == "Error receiving a response from the API"

    def test_get_time_open_returns_correct_difference(self, pull_requests_data):
        with freeze_time("2022-01-02 12:00:00"):
            created_at = datetime.datetime(2022, 1, 1, 11, 30, 0)
            assert pull_requests_data.get_time_open(created_at) == datetime.timedelta(hours=24, minutes=30)

    def test_list_pull_requests_returns_expected_data(self, pull_requests_data, pr_response_data):
        mock_make_request = MagicMock(return_value=pr_response_data)
        mock_get_time_open = MagicMock(return_value=datetime.timedelta(days=1))
        mock_list_commits = MagicMock(return_value=["commit1", "commit2"])
        mock_list_comments = MagicMock(return_value=["comment1", "comment2"])

        with patch("script.PullRequestsData.make_request", mock_make_request):
            with patch("script.PullRequestsData.get_time_open", mock_get_time_open):
                with patch("script.PullRequestsData.list_commits", mock_list_commits):
                    with patch("script.PullRequestsData.list_comments", mock_list_comments):
                        pull_requests = pull_requests_data.list_pull_requests()
        assert pull_requests == [
            (1, "Title 1", "user1", "2021-01-01T10:00:00Z", "2021-01-01T10:00:00Z", datetime.timedelta(days=1),
             ["commit1", "commit2"], ["comment1", "comment2"], [{"login": "reviewer1", "id": 1, "type": "User"}]),
            (2, "Title 2", "user2", "2021-01-02T10:00:00Z", "2021-01-02T10:00:00Z", datetime.timedelta(days=1),
             ["commit1", "commit2"], ["comment1", "comment2"], [{"login": "reviewer2", "id": 2, "type": "User"}])]

    def test_list_pull_requests_handles_empty_response(self, pull_requests_data, pr_response_data):
        mock_make_request = MagicMock(return_value=[])
        mock_get_time_open = MagicMock(return_value=[])
        mock_list_commits = MagicMock(return_value=[])
        mock_list_comments = MagicMock(return_value=[])

        with patch("script.PullRequestsData.make_request", mock_make_request):
            with patch("script.PullRequestsData.get_time_open", mock_get_time_open):
                with patch("script.PullRequestsData.list_commits", mock_list_commits):
                    with patch("script.PullRequestsData.list_comments", mock_list_comments):
                        pull_requests = pull_requests_data.list_pull_requests()
        assert pull_requests == []

    def test_list_comments_returns_expected_data(self, pull_requests_data):
        url = "https://api.github.com/repos/test_user/test_repo/pulls/1/comments"
        data = [
            {
                "user": {
                    "login": "test_user_1"
                },
                "body": "Test comment 1"
            },
            {
                "user": {
                    "login": "test_user_2"
                },
                "body": "Test comment 2"
            }
        ]

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = data
        with patch.object(requests, 'get', return_value=response) as mock_get:
            result = pull_requests_data.list_comments(url)

        mock_get.assert_called_once_with(url)

        expected_result = [
            ("test_user_1", "Test comment 1"),
            ("test_user_2", "Test comment 2")
        ]
        assert result == expected_result

    def test_list_comments_handles_empty_response(self, pull_requests_data):
        url = "https://api.github.com/repos/test_user/test_repo/pulls/1/comments"
        data = []
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = data
        with patch.object(requests, 'get', return_value=response) as mock_get:
            result = pull_requests_data.list_comments(url)

        mock_get.assert_called_once_with(url)
        assert result == []

    def test_list_commits_returns_expected_data(self, pull_requests_data):
        with patch("script.PullRequestsData.make_request") as mock_make_request:
            mock_data = [
                {"url": "commit_url_1", "sha": "commit_sha_1"},
                {"url": "commit_url_2", "sha": "commit_sha_2"}
            ]
            mock_commit_data = {
                "commit": {
                    "message": "commit message",
                    "committer": {
                        "name": "committer name"
                    }
                }
            }
            mock_make_request.side_effect = [mock_data, mock_commit_data, mock_commit_data]

            result = pull_requests_data.list_commits(url="pull_request_url")
            assert result == [
                ("commit_sha_1", "commit message", "committer name"),
                ("commit_sha_2", "commit message", "committer name")
            ]

    def test_list_commits_handles_empty_response(self, pull_requests_data):
        with patch("script.PullRequestsData.make_request") as mock_make_request:
            mock_data = []
            mock_commit_data = {}
            mock_make_request.side_effect = [mock_data, mock_commit_data, mock_commit_data]

            result = pull_requests_data.list_commits(url="pull_request_url")
            assert result == []

    def test_save_pull_requests_csv_created_file_successfuly(self, pull_requests_data, mock_pull_requests):
        pull_requests_data.save_pull_requests_csv()
        file_path = f"test-repo_startstopstep.csv"
        assert os.path.exists(file_path)
        df = pd.read_csv(file_path)
        assert list(df.columns) == ["PR №", "Title", "Author", "Created At", "Updated At", "Time open", "Commits",
                                    "Comments", "Reviewers"]
        assert len(df) == 2
        assert df.iloc[0].tolist() == [1, "Title 1", "Author 1", "2022-01-01T00:00:00Z", "2022-01-02T00:00:00Z", 1, 1,
                                       1, "['Reviewer 1']"]
        assert df.iloc[1].tolist() == [2, "Title 2", "Author 2", "2022-02-01T00:00:00Z", "2022-02-02T00:00:00Z", 2, 2,
                                       2, "['Reviewer 2']"]
