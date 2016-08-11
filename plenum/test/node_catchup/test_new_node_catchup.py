from typing import Iterable

import pytest
from plenum.common.util import getlogger
from plenum.test.eventually import eventually
from plenum.test.helper import sendReqsToNodesAndVerifySuffReplies, TestNode, \
    checkNodesConnected
from plenum.test.node_catchup.helper import checkNodeLedgersForEquality


logger = getlogger()


txnCount = 5


def checkNodeDisconnectedFrom(needle: str, haystack: Iterable[TestNode]):
    """
    Check if the node name given by `needle` is disconnected from nodes in `haystack`
    :param needle: Node name which should be disconnected from nodes from `haystack`
    :param haystack: nodes who should be disconnected from `needle`
    :return:
    """
    assert all([needle not in node.nodestack.connecteds for node in haystack])


@pytest.fixture("module")
def newNodeCaughtUp(txnPoolNodeSet, nodeSetWithNodeAddedAfterSomeTxns):
    looper, newNode, _, _ = nodeSetWithNodeAddedAfterSomeTxns
    looper.run(eventually(checkNodeLedgersForEquality, newNode,
                          *txnPoolNodeSet[:4], retryWait=1, timeout=5))


def testNewNodeCatchup(newNodeCaughtUp):
    """
    A new node that joins after some transactions should eventually get
    those transactions.
    TODO: Test correct statuses are exchanged
    TODO: Test correct consistency proofs are generated
    :return:
    """
    pass


# TODO: This test passes but it is observed that PREPAREs are not received at
# newly added node. If the stop and start steps are omitted then PREPAREs are
# received. Conclusion is that due to node restart, RAET is losing messages
# but its weird since prepares and commits are received which are sent before
# and after prepares, respectively. Here is the pivotal link
# https://www.pivotaltracker.com/story/show/127897273
def testNodeCatchupAfterRestart(newNodeCaughtUp, txnPoolNodeSet,
                                nodeSetWithNodeAddedAfterSomeTxns):
    """
    A node that restarts after some transactions should eventually get the
    transactions which happened while it was down
    :return:
    """

    looper, newNode, _, client = nodeSetWithNodeAddedAfterSomeTxns
    logger.debug("Stopping node {} with pool ledger size {}".format(newNode.name, newNode.poolManager.txnSeqNo))
    newNode.stop()
    # for n in txnPoolNodeSet[:4]:
    #     for r in n.nodestack.remotes.values():
    #         if r.name == newNode.name:
    #             r.removeStaleCorrespondents()
    # looper.run(eventually(checkNodeDisconnectedFrom, newNode.name,
    #                       txnPoolNodeSet[:4], retryWait=1, timeout=5))
    # TODO: Check if the node has really stopped processing requests?
    logger.debug("Sending requests")
    sendReqsToNodesAndVerifySuffReplies(looper, client, 5)
    logger.debug("Starting the stopped node, {}".format(newNode.name))
    newNode.start(looper.loop)
    looper.run(eventually(checkNodesConnected, txnPoolNodeSet, retryWait=1,
                          timeout=5))
    logger.debug("{}".format(newNode.poolManager.txnSeqNo))
    looper.run(eventually(checkNodeLedgersForEquality, newNode,
                          *txnPoolNodeSet[:4], retryWait=1, timeout=15))


def testNodeDoesNotParticipateUntilCaughtUp(txnPoolNodeSet,
                                            nodeSetWithNodeAddedAfterSomeTxns):
    """
    A new node that joins after some transactions should stash new transactions
    until it has caught up
    :return:
    """
    looper, newNode, _, client = nodeSetWithNodeAddedAfterSomeTxns
    sendReqsToNodesAndVerifySuffReplies(looper, client, 5)

    for node in txnPoolNodeSet[:4]:
        for replica in node.replicas:
            for commit in replica.commits.values():
                assert newNode.name not in commit.voters
            for prepare in replica.prepares.values():
                assert newNode.name not in prepare.voters