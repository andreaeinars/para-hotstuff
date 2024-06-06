#include <iostream>
#include <fstream>
#include <unistd.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <stdlib.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <string>
#include <cstring>
#include <thread>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/rand.h>

#include "utils/Message.h"
#include "utils/RData.h"
#include "utils/RDataPara.h"
#include "utils/Signs.h"
#include "utils/Nodes.h"
#include "utils/KeysFun.h"
#include "handlers/Handler.h"
#include <csignal>
#include <atomic>



std::atomic<bool> pauseRequested(false);
std::atomic<bool> resumeRequested(false);

void signalHandler(int signal) {
    if (signal == SIGUSR1) {
        std::cout << "Handling SIGUSR1 - Pausing operations." << std::endl;
        pauseRequested.store(true);
    } else if (signal == SIGUSR2) {
        std::cout << "Handling SIGUSR2 - Resuming operations." << std::endl;
        resumeRequested.store(true);
    } else {
        std::cout << "Handling signal: " << signal << std::endl;
    }
}


int main(int argc, char const *argv[]) {
  fd_set read_fds;
  fd_set write_fds;
  KeysFun kf;

  std::signal(SIGUSR1, signalHandler);
  std::signal(SIGUSR2, signalHandler);

  // Geting inputs
  if (DEBUG) std::cout << KYEL << "parsing inputs" << KNRM << std::endl;

  unsigned int myid = 0;
  if (argc > 1) { sscanf(argv[1], "%d", &myid); }
  std::cout << KYEL << "[id=" << myid << "]" << KNRM << std::endl;

  unsigned int numFaults = 1;
  if (argc > 2) { sscanf(argv[2], "%d", &numFaults); }
  std::cout << KYEL << "[" << myid << "]#faults=" << numFaults << KNRM << std::endl;

  unsigned int constFactor = 3; // default value: by default, there are 3f+1 nodes
  if (argc > 3) { sscanf(argv[3], "%d", &constFactor); }
  std::cout << KYEL << "[" << myid << "]constFactor=" << constFactor << KNRM << std::endl;

  unsigned int numViews = 10;
  if (argc > 4) { sscanf(argv[4], "%d", &numViews); }
  std::cout << KYEL << "[" << myid << "]#views=" << numViews << KNRM << std::endl;

  double timeout = 100; // timeout in seconds
  if (argc > 5) { sscanf(argv[5], "%lf", &timeout); }
  std::cout << KYEL << "[" << myid << "]timeout=" << timeout << KNRM << std::endl;

  unsigned int maxBlocksInView = 10;  // default value
  if (argc > 6) { sscanf(argv[6], "%d", &maxBlocksInView); }
  std::cout << KYEL << "[" << myid << "]maxBlocksInView=" << maxBlocksInView << KNRM << std::endl;

  float forceRecover = 0.0f;  // default value
  if (argc > 7) { sscanf(argv[7], "%f", &forceRecover); }
  std::cout << KYEL << "[" << myid << "]forceRecover=" << forceRecover << KNRM << std::endl;

  int byzantine = -1;  // default value
  if (argc > 8) { sscanf(argv[8], "%d", &byzantine); }
  std::cout << KYEL << "[" << myid << "]byzantine=" << byzantine << KNRM << std::endl;



  // -- Public key
  KEY priv;
  // Set private key - nothing special to do for EC
#if defined(KK_RSA4096) || defined(KK_RSA2048)
  priv = RSA_new();
#endif

// NOTE: For now, when using the accumulator, all nodes use the same keys, as public keys need to be shared
// between 'trusted' components and 'normal' components, and currently keys are hard coded in trusted components.
// We only do that for ec256, because that's the only one we use really right now.
// We do the same for public keys below.
#if defined(KK_EC256)
  BIO *bio = BIO_new(BIO_s_mem());
  int w = BIO_write(bio,priv_key256,sizeof(priv_key256));
  priv = PEM_read_bio_ECPrivateKey(bio, NULL, NULL, NULL);
#else
  if (kf.loadPrivateKey(myid,&priv)) {
    std::cout << KYEL << "loading private key failed" << KNRM << std::endl;
    return 0;
  }
#endif

#ifdef KK_EC256
  if (DEBUG1) { std::cout << KYEL << "checking private key" << KNRM << std::endl; }
  if (!EC_KEY_check_key(priv)) {
    std::cout << KYEL << "invalid key" << KNRM << std::endl;
  }
  if (DEBUG1) { std::cout << KYEL << "checked private key (sign size=" << ECDSA_size(priv) << ")" << KNRM << std::endl; }
#endif

  unsigned int numNodes = (constFactor*numFaults)+1;
  std::string confFile = "config";
  Nodes nodes(confFile,numNodes);

  // -- Public keys
  for (unsigned int i = 0; i < numNodes; i++) {
    //public key
    KEY pub;
    // Set public key - nothing special to do for EC
#if defined(KK_RSA4096) || defined(KK_RSA2048)
    pub = RSA_new();
#endif
#if defined(KK_EC256)
    BIO *bio = BIO_new(BIO_s_mem());
    int w = BIO_write(bio,pub_key256,sizeof(pub_key256));
    pub = PEM_read_bio_EC_PUBKEY(bio, NULL, NULL, NULL);
#else
    kf.loadPublicKey(i,&pub);
#endif
    if (DEBUG) std::cout << KMAG << "id: " << i << KNRM << std::endl;
    nodes.setPub(i,pub);
  }
  // Initializing handler
  if (DEBUG) std::cout << KYEL << "initializing handler" << KNRM << std::endl;

  long unsigned int size = std::max({sizeof(MsgTransaction), sizeof(MsgReply), sizeof(MsgStart)});

  #if defined(BASIC_BASELINE)
  size = std::max({size,
                   sizeof(MsgNewView),
                   sizeof(MsgPrepare),
                   sizeof(MsgLdrPrepare),
                   sizeof(MsgPreCommit),
                   sizeof(MsgCommit)});
  #elif defined(CHAINED_BASELINE)
  size = std::max({size,
                   sizeof(MsgNewViewCh),
                   sizeof(MsgLdrPrepareCh),
                   sizeof(MsgPrepareCh)});
  #elif defined(PARALLEL_HOTSTUFF) 
  size = std::max({size,
                  sizeof(MsgNewViewPara),
                  sizeof(MsgPreparePara),
                  // sizeof(MsgRecoverPara),
                  (sizeof(MsgRecoverPara) + maxBlocksInView * sizeof(PBlock)),
                  sizeof(MsgLdrRecoverPara),
                  sizeof(MsgVerifyPara),
                  sizeof(MsgLdrPreparePara),
                  sizeof(MsgPreCommitPara),
                  sizeof(MsgCommitPara)});  
  #endif

  if (DEBUG0) {
    std::cout << KYEL << "[" << myid << "]sizes"
              << ":newview="        << sizeof(MsgNewView)
              << ":prepare="        << sizeof(MsgPrepare)
              << ":ldrprepare="     << sizeof(MsgLdrPrepare)
              << ":precommit="      << sizeof(MsgPreCommit)
              << ":commit="         << sizeof(MsgCommit)
              << ":transaction="    << sizeof(MsgTransaction)
              << KNRM << std::endl;
  }
  if (DEBUG0) std::cout << KYEL << "[" << myid << "]max-msg-size=" << size << KNRM << std::endl;
  PeerNet::Config pconfig;
  pconfig.max_msg_size(2*size);
  ClientNet::Config cconfig;
  cconfig.max_msg_size(2*size);
  if (DEBUG1) std::cout << KYEL << "[" << myid << "]starting handler" << KNRM << std::endl;
  Handler handler(kf,myid,timeout,constFactor,numFaults,numViews,nodes,priv,pconfig,cconfig, maxBlocksInView, forceRecover, byzantine);

  return 0;
};
