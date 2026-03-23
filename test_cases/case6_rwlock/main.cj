// 测试用例6: RWLock读写锁保护
// 使用读写锁保护共享变量，无竞争

main() {
    var counter: Int64 = 0
    let rwlock = RWLock()
    
    // 线程1: 读操作
    spawn {
        rwlock.readLock()
        let value = counter  // 读操作，受保护
        rwlock.readUnlock()
    }
    
    // 线程2: 写操作
    spawn {
        rwlock.writeLock()
        counter = counter + 1  // 写操作，受保护
        rwlock.writeUnlock()
    }
    
    println(counter)
}