// case43: 读写锁混合测试
// 测试读写锁的正确使用（无竞争）

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
        let value = data  // 多个读可以并发
        rwlock.unlock()
    }
    
    spawn {
        rwlock.writeLock()
        data = 100  // 写操作
        rwlock.unlock()
    }
    
    spawn {
        rwlock.writeLock()
        data = 200  // 写操作
        rwlock.unlock()
    }
}