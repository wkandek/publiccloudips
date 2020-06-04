import gather_publiccloud_ips


def test_get_aws():
    rs = {}
    pv = {}
    rs, pv = gather_publiccloud_ips.get_aws(False, rs, pv)
    assert len(rs) > 2000
    assert len(pv) == 1 

def test_get_azure():
    rs = {}
    pv = {}
    rs, pv = gather_publiccloud_ips.get_azure(False, rs, pv)
    assert len(rs) > 13000
    assert len(pv) == 1 

def test_get_gcp():
    rs = {}
    pv = {}
    rs, pv = gather_publiccloud_ips.get_gcp(rs, pv)
    assert len(rs) > 70 
    assert len(pv) == 1 

def test_get_Oracle():
    rs = {}
    pv = {}
    rs, pv = gather_publiccloud_ips.get_oracle(False, rs, pv)
    assert len(rs) > 200 
    assert len(pv) == 1 

def test_get_generic():
    rs = {}
    pv = {}
    rs, pv = gather_publiccloud_ips.get_generic("ovh", False, rs, pv)
    assert len(rs) > 210 
    assert len(pv) == 1 

def test_get_file():
    rs = {}
    pv = {}
    rs, pv = gather_publiccloud_ips.get_file("alibaba", rs, pv)
    assert len(rs) > 3 
    assert len(pv) == 1 
