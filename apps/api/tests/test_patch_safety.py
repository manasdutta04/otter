from app.schemas import PatchProposal

def test_patch_proposal_accepts_relative_file_paths():
    proposal = PatchProposal(summary="Update a module", files=[{"path": "src/main.py", "content": "print('ok')"}])
    assert proposal.files[0].path == "src/main.py"
