#ifndef MSG_H
#define MSG_H

#include <set>

#include "Nodes.h"
#include "Signs.h"
//#include "Auth.h"
//#include "Auths.h"
#include "Proposal.h"
#include "JBlock.h"
// #include "Transaction.h"


#include "salticidae/msg.h"
#include "salticidae/stream.h"


/////////////////////////////////////////////////////
// Client messages


struct MsgTransaction {
  static const uint8_t opcode = HDR_TRANSACTION;
  salticidae::DataStream serialized;
  Transaction trans;
  Sign sign;
  MsgTransaction(const Transaction &trans, const Sign &sign) : trans(trans),sign(sign) { serialized << trans << sign; }
  MsgTransaction(salticidae::DataStream &&s) { s >> trans >> sign; }
  bool operator<(const MsgTransaction& s) const {
    if (sign < s.sign) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "TRANSACTION[" + trans.prettyPrint() + "," + sign.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(Transaction) + sizeof(Sign)); }
  void serialize(salticidae::DataStream &s) const { s << trans << sign; }
};

struct MsgStart {
  static const uint8_t opcode = HDR_START;
  salticidae::DataStream serialized;
  CID cid;
  Sign sign;
  MsgStart(const CID &cid, const Sign &sign) : cid(cid),sign(sign) { serialized << cid << sign; }
  MsgStart(salticidae::DataStream &&s) { s >> cid >> sign; }
  bool operator<(const MsgStart& s) const {
    if (cid < s.cid) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "START[" + std::to_string(cid) + "," + sign.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(CID) + sizeof(Sign)); }
  void serialize(salticidae::DataStream &s) const { s << cid << sign; }
};

struct MsgReply {
  static const uint8_t opcode = HDR_REPLY;
  salticidae::DataStream serialized;
  unsigned int reply;
  MsgReply(const unsigned int &reply) : reply(reply) { serialized << reply; }
  MsgReply(salticidae::DataStream &&s) { s >> reply; }
  bool operator<(const MsgReply& s) const {
    if (reply < s.reply) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "REPLY[" + std::to_string(reply) + "]";
  }
  unsigned int sizeMsg() { return (sizeof(unsigned int)); }
  void serialize(salticidae::DataStream &s) const { s << reply; }
};



/////////////////////////////////////////////////////
// Basic version - Baseline and Cheap


// TODO: replace Signs by Sign
struct MsgNewView {
  static const uint8_t opcode = HDR_NEWVIEW;
  salticidae::DataStream serialized;
  RData rdata;
  Signs signs;
  MsgNewView(const RData &rdata, const Signs &signs) : rdata(rdata),signs(signs) { serialized << rdata << signs; }
  MsgNewView(salticidae::DataStream &&s) { s >> rdata >> signs; }
  bool operator<(const MsgNewView& s) const {
    if (signs < s.signs) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "NEWVIEW[" + rdata.prettyPrint() + "," + signs.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(RData) + sizeof(Signs)); }
  void serialize(salticidae::DataStream &s) const { s << rdata << signs; }
};

// TODO: replace Signs by Sign
struct MsgLdrPrepare {
  static const uint8_t opcode = HDR_PREPARE_LDR;
  salticidae::DataStream serialized;
  Proposal prop;
  Signs signs;
  MsgLdrPrepare() {}
  MsgLdrPrepare(const Proposal &prop, const Signs &signs) : prop(prop),signs(signs) { serialized << prop << signs; }
  MsgLdrPrepare(salticidae::DataStream &&s) { s >> prop >> signs; }
  bool operator<(const MsgLdrPrepare& s) const {
    if (signs < s.signs) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "LDRPREPARE[" + prop.prettyPrint() + "," + signs.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(Proposal) + sizeof(Signs)); }
  void serialize(salticidae::DataStream &s) const { s << prop << signs; }
};

struct MsgPrepare {
  static const uint8_t opcode = HDR_PREPARE;
  salticidae::DataStream serialized;
  RData rdata;
  Signs signs;
  MsgPrepare(const RData &rdata, const Signs &signs) : rdata(rdata),signs(signs) { serialized << rdata << signs; }
  MsgPrepare(salticidae::DataStream &&s) { s >> rdata >> signs; }
  bool operator<(const MsgPrepare& s) const {
    if (signs < s.signs) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "PREPARE[" + rdata.prettyPrint() + "," + signs.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(RData) + sizeof(Signs)); }
  void serialize(salticidae::DataStream &s) const { s << rdata << signs; }
};

struct MsgPreCommit {
  static const uint8_t opcode = HDR_PRECOMMIT;
  salticidae::DataStream serialized;
  RData rdata;
  Signs signs;
  MsgPreCommit(const RData &rdata, const Signs &signs) : rdata(rdata),signs(signs) { serialized << rdata << signs; }
  MsgPreCommit(salticidae::DataStream &&s) { s >> rdata >> signs; }
  bool operator<(const MsgPreCommit& s) const {
    if (signs < s.signs) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "PRECOMMIT[" + rdata.prettyPrint() + "," + signs.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(RData) + sizeof(Signs)); }
  void serialize(salticidae::DataStream &s) const { s << rdata << signs; }
};

struct MsgCommit {
  static const uint8_t opcode = HDR_COMMIT;
  salticidae::DataStream serialized;
  RData rdata;
  Signs signs;
  MsgCommit(const RData &rdata, const Signs &signs) : rdata(rdata),signs(signs) { serialized << rdata << signs; }
  MsgCommit(salticidae::DataStream &&s) { s >> rdata >> signs; }
  bool operator<(const MsgCommit& s) const {
    if (signs < s.signs) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "COMMIT[" + rdata.prettyPrint() + "," + signs.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(RData) + sizeof(Signs)); }
  void serialize(salticidae::DataStream &s) const { s << rdata << signs; }
};

/////////////////////////////////////////////////////
// Chained Version - Baseline

struct MsgNewViewCh {
  static const uint8_t opcode = HDR_NEWVIEW_CH;
  salticidae::DataStream serialized;
  RData data;
  Sign sign;
  MsgNewViewCh(const RData &data, const Sign &sign) : data(data),sign(sign) { serialized << data << sign; }
  MsgNewViewCh(salticidae::DataStream &&s) { s >> data >> sign; }
  bool operator<(const MsgNewViewCh& s) const {
    if (sign < s.sign) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "NEWVIEW[" + data.prettyPrint() + "," + sign.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(RData) + sizeof(Sign)); }
  void serialize(salticidae::DataStream &s) const { s << data << sign; }
};


struct MsgLdrPrepareCh {
  static const uint8_t opcode = HDR_PREPARE_LDR_CH;
  salticidae::DataStream serialized;
  JBlock block;
  Sign sign;
  MsgLdrPrepareCh() {}
  MsgLdrPrepareCh(const JBlock &block, const Sign &sign) : block(block),sign(sign) { serialized << block << sign; }
  MsgLdrPrepareCh(salticidae::DataStream &&s) { s >> block >> sign; }
  bool operator<(const MsgLdrPrepareCh& s) const {
    if (sign < s.sign) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "LDRPREPARE[" + block.prettyPrint() + "," + sign.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(JBlock) + sizeof(Sign)); }
  void serialize(salticidae::DataStream &s) const { s << block << sign; }
};


struct MsgPrepareCh {
  static const uint8_t opcode = HDR_PREPARE_CH;
  salticidae::DataStream serialized;
  RData data;
  Sign sign;
  MsgPrepareCh(const RData &data, const Sign &sign) : data(data),sign(sign) { serialized << data << sign; }
  MsgPrepareCh(salticidae::DataStream &&s) { s >> data >> sign; }
  bool operator<(const MsgPrepareCh& s) const {
    if (sign < s.sign) { return true; }
    return false;
  }
  std::string prettyPrint() {
    return "PREPARE[" + data.prettyPrint() + "," + sign.prettyPrint() + "]";
  }
  unsigned int sizeMsg() { return (sizeof(RData) + sizeof(Sign)); }
  void serialize(salticidae::DataStream &s) const { s << data << sign; }
};



#endif
