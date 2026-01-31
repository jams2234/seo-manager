"""
Custom exceptions for Git Deployer
"""


class GitDeployerError(Exception):
    """Base exception for Git Deployer errors"""
    pass


class GitConfigurationError(GitDeployerError):
    """Raised when Git configuration is invalid or missing"""
    pass


class GitAuthenticationError(GitDeployerError):
    """Raised when Git authentication fails (invalid token, permissions)"""
    pass


class GitCloneError(GitDeployerError):
    """Raised when repository cloning fails"""
    pass


class GitPushError(GitDeployerError):
    """Raised when pushing to remote repository fails"""
    pass


class ProjectDetectionError(GitDeployerError):
    """Raised when no suitable project handler can be found"""
    pass


class MetadataUpdateError(GitDeployerError):
    """Raised when metadata update fails"""
    pass


class FileNotFoundError(GitDeployerError):
    """Raised when target file (layout.tsx, index.html, etc.) is not found"""
    pass
