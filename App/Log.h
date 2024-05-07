#ifndef LOG_H
#define LOG_H

#include <set>
#include <map>


#include "Just.h"
#include "Proposal.h"
// #include "CData.h"
// #include "Void.h"
// #include "Cert.h"
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

  // finds the justification of the highest message in the 'newviews' log for view 'view'
  Just findHighestNv(View view);
  Just firstPrepare(View view);
  Just firstPrecommit(View view);
  Just firstCommit(View view);
  MsgLdrPrepare firstProposal(View view);

  // collects the signatures of the messages in the 'newviews' log for view 'view', upto 'n' signatures
  Signs getNewView(View view, unsigned int n);
  // collects the signatures of the messages in the 'proposals' log for view 'view', upto 'n' signatures
  Signs getPrepare(View view, unsigned int n);
  // collects the signatures of the messages in the 'precommits' log for view 'view', upto 'n' signatures
  Signs getPrecommit(View view, unsigned int n);
  // collects the signatures of the messages in the 'commits' log for view 'view', upto 'n' signatures
  Signs getCommit(View view, unsigned int n);

  
  std::set<MsgNewViewCh> getNewViewCh(View view, unsigned int n);
  Signs getPrepareCh(View view, unsigned int n);

  MsgLdrPrepareCh firstLdrPrepareCh(View view);
  MsgPrepareCh firstPrepareCh(View view);
  Just findHighestNvCh(View view);

  // generates a string to pretty print logs
  std::string prettyPrint();
};


#endif
