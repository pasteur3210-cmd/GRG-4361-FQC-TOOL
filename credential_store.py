"""Windows Credential Manager backed credential, never hard-coded in the EXE."""
SERVICE='GRG-4361-FQC-TOOL'
USER='root'

def get_password():
    import keyring
    return keyring.get_password(SERVICE,USER)

def set_password(password):
    if not password:raise ValueError('Empty router password')
    import keyring
    keyring.set_password(SERVICE,USER,password)
