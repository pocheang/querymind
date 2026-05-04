# Admin Script Secret Handling Design

## Goal

Remove hardcoded administrator passwords from local maintenance scripts while keeping the scripts convenient for terminal-based operations.

## Scope

This design covers:

- `scripts/create_admin.py`
- `scripts/reset_admin_password.py`
- `scripts/test_and_reset_admin.py`
- shared helper logic used by those scripts

This design does not change:

- backend authentication behavior
- database schema
- `scripts/list_users.py` behavior

## Requirements

The updated scripts must:

- stop storing any password literal in source control
- support non-interactive usage through environment variables
- support interactive usage through hidden terminal input when environment variables are missing
- keep default username behavior simple for the `admin` account
- print clear success and failure messages without exposing unnecessary secrets

## Environment Variables

The scripts should prefer environment variables first:

- `ADMIN_USERNAME`
- `ADMIN_ROLE`
- `ADMIN_PASSWORD`
- `ADMIN_NEW_PASSWORD`
- `ADMIN_CURRENT_PASSWORD`

If a required password is missing from the environment, the script should prompt securely with hidden input.

## Proposed Structure

Add a small shared helper module under `scripts/` for:

- reading environment variables with defaults
- prompting for hidden passwords
- locating a user by username

Then update each script:

### `create_admin.py`

- use `ADMIN_USERNAME` with default `admin`
- use `ADMIN_ROLE` with default `admin`
- use `ADMIN_PASSWORD` or secure prompt
- create the user only if it does not already exist

### `reset_admin_password.py`

- use `ADMIN_USERNAME` with default `admin`
- locate the user
- use `ADMIN_NEW_PASSWORD` or secure prompt
- reset the password

### `test_and_reset_admin.py`

- use `ADMIN_USERNAME` with default `admin`
- locate the user
- optionally verify `ADMIN_CURRENT_PASSWORD` if provided
- use `ADMIN_NEW_PASSWORD` or secure prompt
- reset the password
- optionally verify the new password after reset

### `list_users.py`

- leave unchanged

## Error Handling

The scripts should:

- fail fast when the target user does not exist
- reject empty passwords after trimming
- surface backend exceptions in a concise way
- avoid stack traces unless they are already part of the current script behavior and clearly useful

## Security Notes

- no password literals should remain in committed files
- hidden prompts should use `getpass`
- success output should confirm the action without printing the password value by default
- environment-variable support is for automation convenience, but interactive prompting should remain the safe fallback

## Testing

Validation for this change should include:

- interactive create flow without `ADMIN_PASSWORD`
- non-interactive reset flow with `ADMIN_NEW_PASSWORD`
- missing-user failure path
- optional verification path in `test_and_reset_admin.py`
