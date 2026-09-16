def test_memory_store():
    from beau.memory.store import MemoryStore
    import tempfile
    with tempfile.NamedTemporaryFile() as f:
        m = MemoryStore(path=f.name)
        m.save("user: hi", "assistant: hello")
        assert "hello" in m.recall("hi")
