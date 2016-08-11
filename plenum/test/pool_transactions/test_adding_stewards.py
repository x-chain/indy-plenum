import pytest

from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from plenum.common.txn import TXN_TYPE, NEW_STEWARD, TARGET_NYM, DATA
from plenum.test.eventually import eventually
from plenum.test.helper import TestClient, genHa


@pytest.fixture(scope="module")
def tconf(conf, tdir, request):
    oldThreshold = conf.stewardThreshold
    conf.baseDir = tdir
    conf.stewardThreshold = 1

    def reset():
        conf.stewardThreshold = oldThreshold

    request.addfinalizer(reset)
    return conf


def testOnlyAStewardCanAddAnotherSteward(txnPoolNodeSet,
                                         tdirWithPoolTxns, poolTxnClientData,
                                         txnPoolCliNodeReg):
    return checkStewardAdded(poolTxnClientData, tdirWithPoolTxns,
                             txnPoolCliNodeReg)


def testStewardsCanBeAddedOnlyTillAThresholdIsReached(
        tconf, txnPoolNodeSet, tdirWithPoolTxns, poolTxnStewardData,
        txnPoolCliNodeReg):
    return checkStewardAdded(poolTxnStewardData, tdirWithPoolTxns,
                             txnPoolCliNodeReg)


def checkStewardAdded(poolTxnStewardData, tdirWithPoolTxns,
                      txnPoolCliNodeReg):
    with Looper(debug=True) as looper:
        name, sigseed = poolTxnStewardData
        stewardSigner = SimpleSigner(seed=sigseed)
        client = TestClient(name=name,
                            nodeReg=txnPoolCliNodeReg,
                            ha=genHa(),
                            signer=stewardSigner,
                            basedirpath=tdirWithPoolTxns)
        looper.add(client)
        looper.run(client.ensureConnectedToNodes())
        sigseed = b'55555555555555555555555555555555'
        newSigner = SimpleSigner(sigseed)
        client.submit({
            TXN_TYPE: NEW_STEWARD,
            TARGET_NYM: newSigner.verstr,
            DATA: {
                "alias": "Robert"
            }
        })

        def chk():
            assert client.getReply(client.lastReqId) == (None, "NOT_FOUND")

        looper.run(eventually(chk, retryWait=1, timeout=5))