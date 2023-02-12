import datetime

import pandas as pd
import requests

from exceptions import ApiError


class PullRequestsData:
    """
        Retrieve information about pull requests from a given GitHub repository.
    """

    def __init__(self, repo_owner: str, repo_name: str) -> None:
        """
            Initialize the class with the repository owner and name.

            :param repo_owner: Repository owner's GitHub username.
            :param repo_name: Name of the GitHub repository.
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    @staticmethod
    def make_request(url: str) -> list:
        """
            Send a GET request to the specified URL and return the response as a list.

            :param url: URL to send the GET request to.
            :return: Response from the API as a list.
            :raises: ApiError if the status code of the response is not 200 (OK).
        """
        response = requests.get(url)

        if response.status_code != 200:
            raise ApiError("Error receiving a response from the API")

        return response.json()

    @staticmethod
    def get_time_open(created_at: datetime) -> datetime:
        """
            Calculates the difference between the current time and the time a pull request was created.

            :param created_at: The datetime object representing when the pull request was created.
            :return: The difference between the current time and the time the pull request was created.
        """
        now = datetime.datetime.now()
        return now - created_at

    def list_pull_requests(self) -> list:
        """
            Get a list of pull requests for the given repository.

            :return: List of pull requests:
        """
        pull_requests = []
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls"
        data = self.make_request(url)

        for pull_request in data:
            pull_request_commits_url = pull_request["commits_url"]
            pull_request_comments_url = pull_request["comments_url"]
            pull_request_review_requests = [{'login': review['login'],
                                             'id': review['id'],
                                             'type': review['type']}
                                            for review in
                                            pull_request["requested_reviewers"]]
            created_at = datetime.datetime.strptime(pull_request["created_at"], "%Y-%m-%dT%H:%M:%SZ")

            pull_requests.append((pull_request["number"],
                                  pull_request["title"],
                                  pull_request["user"]["login"],
                                  pull_request["created_at"],
                                  pull_request["updated_at"],
                                  self.get_time_open(created_at),
                                  self.list_commits(pull_request_commits_url),
                                  self.list_comments(pull_request_comments_url),
                                  pull_request_review_requests))

        return pull_requests

    def list_commits(self, url: str) -> list:
        """
            Get a list of commits for the given pull request.

            :param url: URL of the pull request's commits API endpoint.
            :return: List of commits in the format: [(commit sha, message, committer name), ...].
        """
        commits = []
        data = self.make_request(url)
        for commit in data:
            commit_url = commit["url"]
            commit_data = self.make_request(commit_url)
            commits.append(
                (commit["sha"],
                 commit_data["commit"]["message"],
                 commit_data["commit"]["committer"]["name"]))

        return commits

    def list_comments(self, url: str) -> list:
        """
            Retrieves comments for a specific pull request.

            :param url: URL to retrieve comments for a pull request.
            :return: List of tuples, each tuple containing author and body of the comment.
        """
        comments = []
        data = self.make_request(url)

        for comment in data:
            comments.append(
                (comment["user"]["login"],
                 comment["body"]))

        return comments

    def save_pull_requests_csv(self) -> None:
        """
            Saves the pull requests information to a CSV file.

            The file name is constructed using the `repo_name` and `repo_owner` attributes of the object.
            The data is retrieved from the `list_pull_requests` method and stored in a pandas DataFrame.
            The data is then saved to a CSV file with the specified file name.
        """
        df = pd.DataFrame(self.list_pull_requests(), columns=["PR №", "Title", "Author",
                                                              "Created At", "Updated At",
                                                              "Time open", "Commits",
                                                              "Comments", "Reviewers"])
        df.to_csv(f"{self.repo_name}_{self.repo_owner}.csv", index=False)

    def print_pull_requests(self) -> None:
        """
            Prints the pull requests information.
        """
        pull_requests = self.list_pull_requests()

        for number, title, user, created_at, updated_at, time_open, commits, comments, review_requests in pull_requests:
            print("Number: ", number)
            print("Title: ", title)
            print("User: ", user)
            print("Created at: ", created_at)
            print("Updated at: ", updated_at)
            print("Time open: ", time_open)
            print("Commits: ")
            for sha, message, committer in commits:
                print("\tSHA: ", sha)
                print("\tMessage: ", message)
                print("\tCommitter: ", committer)
            print("Comments: ")
            for author, body in comments:
                print("\tAuthor: ", author)
                print("\tBody: ", body)
            print("Review requests: ")
            for login, id, type in review_requests:
                print("\tLogin: ", login)
                print("\tId: ", id)
                print("\tType: ", type)
            print("*" * 80)


if __name__ == "__main__":
    pr = PullRequestsData(repo_owner="startstopstep", repo_name="test-repo")
    pr.save_pull_requests_csv()
    pr.print_pull_requests()
