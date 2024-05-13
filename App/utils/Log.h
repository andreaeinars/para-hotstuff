#ifndef LOG_H
#define LOG_H

#include <set>
#include <map>
#include "Just.h"
#include "Proposal.h"
#include "Message.h"

class Log {
 private:
  std::map<View,std::set<MsgNewView>> newviews;
  std::map<View,std::set<MsgPrepare>> prepares;
  std::map<View,std::set<MsgPreCommit>> precommits;
  std::map<View,std::set<MsgCommit>> commits;
  std::map<View,std::set<MsgLdrPrepare>> proposals;

  std::map<View,std::set<MsgNewViewCh>> newviewsCh;
  std::map<View,std::set<MsgPrepareCh>> preparesCh;
  std::map<View,std::set<MsgLdrPrepareCh>> ldrpreparesCh;

  std::map<View,std::set<MsgNewViewPara>> newviewsPara;
  // std::map<View,std::set<MsgPreparePara>> preparesPara;
  // std::map<View,std::set<MsgPreCommitPara>> precommitsPara;
  // std::map<View,std::set<MsgCommitPara>> commitsPara;
  // std::map<View,std::set<MsgLdrPreparePara>> proposalsPara;

  //std::map<View, std::map<unsigned int, std::set<MsgNewViewPara>>> newviewsPara;
  std::map<View, std::map<unsigned int, std::set<MsgPreparePara>>> preparesPara;
  std::map<View, std::map<unsigned int, std::set<MsgPreCommitPara>>> precommitsPara;
  std::map<View, std::map<unsigned int, std::set<MsgCommitPara>>> commitsPara;
  std::map<View, std::map<unsigned int, std::set<MsgLdrPreparePara>>> proposalsPara;


 public:
  Log();

  // those return the number of signatures (0 if the msg is not from a not-yet-heard-from node)
  unsigned int storeNv(MsgNewView msg);
  unsigned int storePrep(MsgPrepare msg);
  unsigned int storePc(MsgPreCommit msg);
  unsigned int storeCom(MsgCommit msg);
  unsigned int storeProp(MsgLdrPrepare msg);

  unsigned int storeNvCh(MsgNewViewCh msg);
  unsigned int storePrepCh(MsgPrepareCh msg);
  unsigned int storeLdrPrepCh(MsgLdrPrepareCh msg);

  unsigned int storeNvPara(MsgNewViewPara msg);
  unsigned int storePrepPara(MsgPreparePara msg);
  unsigned int storePcPara(MsgPreCommitPara msg);
  unsigned int storeComPara(MsgCommitPara msg);
  unsigned int storePropPara(MsgLdrPreparePara msg);

  // finds the justification of the highest message in the 'newviews' log for view 'view'
  Just findHighestNv(View view);
  Just firstPrepare(View view);
  Just firstPrecommit(View view);
  Just firstCommit(View view);
  MsgLdrPrepare firstProposal(View view);

  Just findHighestNvPara(View view);

  // collects the signatures of the messages in the 'newviews' log for view 'view', upto 'n' signatures
  Signs getNewView(View view, unsigned int n);
  // collects the signatures of the messages in the 'proposals' log for view 'view', upto 'n' signatures
  Signs getPrepare(View view, unsigned int n);
  // collects the signatures of the messages in the 'precommits' log for view 'view', upto 'n' signatures
  Signs getPrecommit(View view, unsigned int n);
  // collects the signatures of the messages in the 'commits' log for view 'view', upto 'n' signatures
  Signs getCommit(View view, unsigned int n);

  Signs getNewViewPara(View view, unsigned int n, unsigned int seqNumber);
  Signs getPreparePara(View view, unsigned int n, unsigned int seqNumber);
  Signs getPrecommitPara(View view, unsigned int n, unsigned int seqNumber);
  Signs getCommitPara(View view, unsigned int n, unsigned int seqNumber);
  
  std::set<MsgNewViewCh> getNewViewCh(View view, unsigned int n);
  Signs getPrepareCh(View view, unsigned int n);

  MsgLdrPrepareCh firstLdrPrepareCh(View view);
  MsgPrepareCh firstPrepareCh(View view);
  Just findHighestNvCh(View view);


  // generates a string to pretty print logs
  std::string prettyPrint();

  bool hasPrecommitForSeq(View view, unsigned int seqNumber);
};

#endif