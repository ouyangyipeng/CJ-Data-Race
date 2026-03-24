// case30: 读写锁分离测试
// 测试RWLock的读写分离特性

main() {
    var data: Int64 = 0
    let rwlock = RWLock()
    
    spawn {
        rwlock.readLock()
        let value = data  // 读操作
        rwlock.unlock()
    }
    
    spawn {
        rwlock.readLock()
        let value = data  // 读操作（多个读可以并发）
        rwlock.unlock()
    }
    
    spawn {
        rwlock.writeLock()
        data = 100  // 写操作
        rwlock.unlock()
    }
}